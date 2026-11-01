# SPDX-License-Identifier: GPL-3.0-only
# Copyright © 2026 Lumin0usX

"""NÜVEL Studio launcher. Use --classic for the previous Tk interface."""
import sys

if __name__ == '__main__':
    if sys.argv[1:2] in (['--uninstall'], ['--finish-uninstall']):
        from app_uninstall import main as uninstall_main
        raise SystemExit(uninstall_main(sys.argv[2:] if sys.argv[1] == '--uninstall' else sys.argv[1:]))
    elif sys.argv[1:2] == ['--apply-update']:
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
