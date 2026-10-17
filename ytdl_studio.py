"""YTDL Studio launcher. Use --classic for the previous Tk interface."""
import sys

if __name__ == '__main__':
    if '--classic' in sys.argv:
        import tkinter as tk
        from legacy_tk import YTDLStudio
        root = tk.Tk()
        YTDLStudio(root)
        root.mainloop()
    else:
        from glass_app import main
        main()
