import os
import sys
import platform
from NiimPrintX.ui.main import LabelPrinterApp

from NiimPrintX.ui.SplashScreen import SplashScreen


def load_libraries():
    if hasattr(sys, '_MEIPASS'):
        base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
        magick_path = os.path.join(base_path, 'imagemagick')
        env = os.environ.copy()

        if platform.system() == "Linux" or platform.system() == "Darwin":
            env['MAGICK_HOME'] = magick_path
            env['PATH'] = os.path.join(magick_path, 'bin') + os.pathsep + env['PATH']
            env['LD_LIBRARY_PATH'] = os.path.join(magick_path, 'lib') + os.pathsep + env.get(
                'LD_LIBRARY_PATH', '')
            env['MAGICK_CONFIGURE_PATH'] = os.path.join(magick_path, 'etc', 'ImageMagick-7')
            os.environ['DYLD_LIBRARY_PATH'] = magick_path + ':' + os.environ.get('DYLD_LIBRARY_PATH', '')
        elif platform.system() == "Windows":
            env['MAGICK_HOME'] = magick_path
            env['PATH'] = magick_path + os.pathsep + env['PATH']


load_libraries()


if __name__ == "__main__":
    try:
        app = LabelPrinterApp()
        splash = SplashScreen(app)  # Create the splash screen

        # Hide the main window initially
        # app.withdraw()
        app.load_resources()  # Start loading resources; it shows the main window itself after 5s
        app.after(5000, splash.destroy)  # Automatically destroy the splash screen after 5 seconds
        app.mainloop()
    except Exception as e:
        print(f"Error {e}")
        raise e
