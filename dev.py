import os

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from app import app

# Define the directory to watch
template_dir = 'templates'

class TemplateChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.html'):
            print("Detected change in HTML template. Reloading server...")
            os.system("pkill -f flask")  # Kill Flask server
            os.system("python app.py &")  # Restart Flask server

if __name__ == "__main__":
    observer = Observer()
    observer.schedule(TemplateChangeHandler(), template_dir, recursive=True)
    observer.start()

    try:
        app.run(debug=True)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
