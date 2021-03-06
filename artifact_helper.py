from screen_processor import ScreenProcessor, numpy_flip
from concurrent.futures import ThreadPoolExecutor
from artibuff_scrape import Artibuff_Card
from tier_list_scrape import read_tier_text, Tier_List_Card
import os
import sys
import pickle
import webbrowser
import time
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk
from mss import mss

path_root = os.path.dirname(sys.modules['__main__'].__file__)

def path(filename):
    global path_root
    return os.path.join(path_root, filename)

def OpenUrl():
    webbrowser.open_new('https://github.com/eoakley/artifacthelper')

def load_pickle(file_name="card_dict.pkl"):
    try:
        with open(file_name, 'rb') as handle:
            b = pickle.load(handle)
        return b
    except Exception as err:
        print("Error loading pickle")
        print(err)

executor = ThreadPoolExecutor(40)

stats = load_pickle(path('resources/card_dict.pkl'))

tiers = read_tier_text(path('tier_list.txt'))

sp = None

def compare_images(img, img2):
    dif = np.mean(np.abs(img.astype(int) - img2.astype(int)))
    return dif

def save_debugg_screenshot(ss, card_grid):

    red = [255, 0, 0]
    #draw grid on screenshot for debugging
    for row in range(2):
        for col in range(6):
            #quatro cantos da carta
            top, left, bottom, right = card_grid[row, col, :]

            #paint square with red.
            #ss.shape = (1080, 1920, 3)
            ss[top:bottom, left, :] = red
            ss[top:bottom, right, :] = red
            ss[top, left:right, :] = red
            ss[bottom, left:right, :] = red

    #save screenshot
    ss_img = Image.fromarray(ss)
    ss_img.save(path('screen_shot_debugg.png'),"PNG")

########### TODO: need to update this
def get_draft_state(screen_width, screen_height):
    with mss() as sct:
        mon = sct.monitors[1]

        monitor = {
            "top": mon["top"] + 48*screen_height//1080,
            "left": mon["left"] + 1385*screen_width//1920,
            "width": 56*screen_width//1920,
            "height": 52*screen_height//1080,
            "mon": 1,
        }

        # Grab the data
        img = sct.grab(monitor)

        return numpy_flip(img)

def destroy_list(ll, root):
    #destroy list if exists:
    for ele in ll:
        try:
            ele.destroy()
        except tk.TclError as e:
            pass
    
    ll = []
    root.update()

def auto_hide(ll, root, screen_width, screen_height):
    global flag_auto_hide
    thresh = 5
    img2 = get_draft_state(screen_width, screen_height)
    
    while(1):
        #checks pixels
        img = get_draft_state(screen_width, screen_height)
        
        #compare
        dif = compare_images(img, img2)
        
        #mouse
        mx, my = root.winfo_pointerxy()
        
        inside = mx >= (1385-40)*screen_width//1920 and mx <= (1385 + 56 +20)*screen_width//1920 and my >= (48 -20)*screen_height//1080 and my <= (48 + 52+20)*screen_height//1080
        if dif > thresh and not inside:
            destroy_list(ll, root)
            img2 = img
            flag_auto_hide = False
            break
        
        #sleeps
        time.sleep(.2)
        

label_list = []
flag_swap = 1
coisas = []

flag_auto_hide = False

bg_color = 'magenta'

def btnProcessScreen(ll, root, screen_width, screen_height):
    global flag_auto_hide, sp
    #inicia auto hide
    if not flag_auto_hide:
        executor.submit(auto_hide, ll, root, screen_width, screen_height)
        flag_auto_hide = True
    
    destroy_list(ll, root)
    
    ss, (cards, scores, card_grid) = sp.process_screen()
        
    # from_top, from_left = 139*screen_height//1080, 68*screen_width//1920
    # space_h, space_w = 344*screen_height//1080, 211*screen_width//1920
    
    #if all cards are empty cards or error in process screen,
    #show error in UI
    if len(cards) == 0 or cards.count('Empty Card') == 12:
        label_height = 80
        label_width = 240

        txt = "Error detecting cards.\nAre you on draft screen?"
        #save ss for debugg
        if len(card_grid) > 1:
            save_debugg_screenshot(ss, card_grid)
            txt += "\n\nSaved screen_shot_debugg.png \non installation dir."
            label_height=160
            label_width=340
            
        l = tk.Label(root, text=txt, justify='center', bg='#222', 
                    fg="#DDD", font=("Helvetica 14"), borderwidth=3, relief="solid")
        
        l.place(x = screen_width//2-label_width, y = 120, width=label_width, height=label_height)
        
        ll.append(l)

        return None

    save_debugg_screenshot(ss, card_grid)
    for row in range(2):
        for col in range(6):
            #quatro cantos da carta
            top, left, bottom, right = card_grid[row, col, :]
            
            card_name = cards[row*6+col]
            card_score = scores[row*6+col]

            if card_name == 'Empty Slot':
                continue
                
            try:
                wr = stats[card_name]['str']
                tier = tiers[card_name]
            except:
                tier = ''
                wr = ''
                
            if card_name == 'Empty Card':
                continue
            elif card_name not in stats.keys():
                print('Card not found:', card_name)
                continue
                
            elif card_name not in tiers.keys():
                tier = '?'
                
            max_len_name = 20
            if len(card_name) > max_len_name:
                card_name = card_name[:max_len_name-2] + '..'
            txt = card_name.rjust(20) + '\n' + str(wr).rjust(20) + '\n' + str(tier).rjust(20)
            l = tk.Label(root, text=txt, justify='right', bg='#222', 
                      fg="#DDD", font=("Helvetica 10 bold"), borderwidth=3, relief="solid")
            
            l.place(anchor='ne', x = left+50, y = top, width=145, height=61)
            
            ll.append(l)
        
def close_window(root): 
    root.destroy()
    
def swap_window(root, screen_width, screen_height, first_time=False):
    global coisas, flag_swap, flag_auto_hide, label_list, sp
    flag_auto_hide = False
    
    #clean stuff
    destroy_list(coisas, root)
    destroy_list(label_list, root)
    
    if flag_swap == 0:
        root.call('wm', 'attributes', '.', '-topmost', '1')
        root.call('wm', 'attributes', '.', '-transparentcolor', bg_color)
        root.title("Artifact Helper")
        root.geometry("1400x740+%d+%d" % (100,0))
        root.configure(background=bg_color)
        root.lift()
        root.overrideredirect(1) #Remove border

        logo = ImageTk.PhotoImage(Image.open(path('resources/banner_1.png')))
        btnImgScan = ImageTk.PhotoImage(Image.open(path('resources/btn_scan_1.png')))

        lg = tk.Label(root, image=logo, borderwidth=0, relief="solid")
        lg.image = logo
        lg.place(x = 400, y = 1, width=816, height=105)
        coisas.append(lg)

        top_border = 60
        left_space = 860
        b = tk.Button(root, text="Scan Cards", command=lambda: btnProcessScreen(label_list, root, screen_width, screen_height), bg='#CCC', relief='flat', borderwidth=0)
        b.config(image=btnImgScan)
        b.image = btnImgScan
        b.place(x = left_space-96, y = top_border-32, width=166, height=57)
        coisas.append(b)

        b2 = tk.Button(root, text="?", command=lambda: OpenUrl(), bg='#CCC')
        b2.place(x = left_space+313, y = 3, width=20, height=25)
        coisas.append(b2)

        b3 = tk.Button(root, text="X", command = lambda: swap_window(root, screen_width, screen_height), bg='#CCC')
        b3.place(x = left_space+334, y = 3, width=20, height=25)
        coisas.append(b3)

        flag_swap = 1
    else:
        root.call('wm', 'attributes', '.', '-topmost', '0')
        root.title("Artifact Helper")

        #sp global
        sp = ScreenProcessor(path('resources/dhash_v1.pkl'), path('resources/label_to_name.pkl'), screen_width, screen_height)

        root.geometry("800x340+%d+%d" % (screen_width/2-400,screen_height/2-300))
        root.configure(background="#333")
        root.overrideredirect(0) # border 
        root.resizable(False, False)

        if not first_time:
            #root.lower()
            pass
        
        logo = ImageTk.PhotoImage(Image.open(path('resources/launcher_bg.png')))
        btnImgScan = ImageTk.PhotoImage(Image.open(path('resources/btn_launch_overlay.png')))

        lg = tk.Label(root, image=logo, borderwidth=0, relief="solid")
        lg.image = logo
        lg.place(x = 0, y = 1, width=800, height=600)
        coisas.append(lg)

        b = tk.Button(root, text="Launch Overlay", command=lambda: swap_window(root, screen_width, screen_height), bg='#CCC', relief='flat', borderwidth=0)
        b.config(image=btnImgScan)
        b.image = btnImgScan
        b.place(x = 84, y = 171, width=205, height=57)
        coisas.append(b)
        
        b2 = tk.Button(root, text="?", command=lambda: OpenUrl(), bg='#CCC')
        b2.place(x = 776, y = 5, width=20, height=25)
        coisas.append(b2)
        
        flag_swap = 0

def main():
    root = tk.Tk()
    root.iconbitmap(path('favicon.ico'))

    screen_width = root.winfo_screenwidth() # width of the screen
    screen_height = root.winfo_screenheight() 
    
    swap_window(root, screen_width, screen_height, first_time=True)
    
    root.mainloop()

if __name__ == "__main__":
    #run
    main()