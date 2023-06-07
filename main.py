import webview
from api import Api

def main():
    api = Api()
    window = webview.create_window('Discord Bot GUI', 'index.html', js_api=api, width=800, height=650, resizable=False, frameless=True)
    api.set_window(window)
    webview.start(debug=False)

if __name__ == '__main__':
    main()
