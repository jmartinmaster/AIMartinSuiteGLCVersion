from app.controllers.app_controller import Dispatcher
from launcher import __module_name__, __version__, run_application
from app.app_platform import apply_app_icon, apply_windows_app_id, apply_windows_window_icons, convert_png_to_ico, get_obsolete_local_executables, get_work_area_insets


if __name__ == "__main__":
    import sys

    run_application(main_module=sys.modules[__name__])
