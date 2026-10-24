"""NÜVEL Studio launcher. Use --classic for the previous Tk interface."""
import sys

if __name__ == '__main__':
    if sys.argv[1:2] == ['--apply-update']:
        from update_installer import helper_main
        raise SystemExit(helper_main(sys.argv[2], sys.argv[3]))
    elif '--classic' in sys.argv:
        import tkinter as tk
        from legacy_tk import NuvelStudio
        root = tk.Tk()
        NuvelStudio(root)
        root.mainloop()
    else:
        from glass_app import main
        main()
