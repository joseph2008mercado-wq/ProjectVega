"""Launch with python -m vega.app. Preview always starts muted."""

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device-index", type=int, help="Initial Titan index if multiple controllers are attached")
    args = parser.parse_args(argv)
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print('Install desktop dependencies: python -m pip install -e ".[desktop]"', file=sys.stderr)
        return 2

    from vega.app.window import VegaWindow
    from vega.audio.preview import PreviewSynth
    from vega.audio.pygame_backend import PygameAudioBackend
    from vega.input.desktop_source import DesktopInputSource
    from vega.runtime import VegaRuntime
    from vega.settings import SettingsStore

    app = QApplication(sys.argv[:1])
    app.setApplicationName("Project Vega")
    app.setOrganizationName("ProjectVega")
    store = SettingsStore()
    settings = store.load()
    preview = PreviewSynth(PygameAudioBackend(), settings.preview_volume)
    runtime = VegaRuntime(DesktopInputSource(device_index=args.device_index), preview, settings)
    window = VegaWindow(runtime, store)
    window.show()
    try:
        return app.exec()
    finally:
        runtime.close()


if __name__ == "__main__":
    raise SystemExit(main())
