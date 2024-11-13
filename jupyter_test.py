import dash
from dash import html, dcc
from jupyter_server.serverapp import ServerApp
import nest_asyncio
import os
import multiprocessing
import time
import asyncio
import logging
from traitlets.config import Config
import shutil

# Enable nested event loops (required for Jupyter)
nest_asyncio.apply()


def run_jupyter_server(notebook_dir, port):
    """Standalone function to run Jupyter server"""
    try:
        asyncio.set_event_loop(asyncio.new_event_loop())
        logging.getLogger('tornado.access').setLevel(logging.WARNING)

        # Create a config object
        c = Config()
        c.ServerApp.port = port
        c.ServerApp.ip = '0.0.0.0'
        c.ServerApp.root_dir = notebook_dir
        c.ServerApp.open_browser = False
        c.ServerApp.allow_root = True
        c.ServerApp.allow_origin = '*'
        c.ServerApp.allow_credentials = True
        c.ServerApp.disable_check_xsrf = True
        c.ServerApp.token = ''
        c.ServerApp.password = ''
        c.ServerApp.password_required = False
        c.ServerApp.base_url = '/'
        c.IdentityProvider.token = ''
        c.ServerApp.tornado_settings = {
            'headers': {
                'Content-Security-Policy': "frame-ancestors 'self' http://localhost:* http://127.0.0.1:*"
            }
        }

        server = ServerApp.instance(config=c)
        server.initialize([])
        server.start()
    except Exception as e:
        print(f"Error starting Jupyter server: {str(e)}")
        raise


class JupyterDashIntegration:
    def __init__(self, notebook_dir='jupyter'):
        self.notebook_dir = os.path.abspath(notebook_dir)
        self.jupyter_port = 8888
        self.process = None

    def start_jupyter_server(self):
        """Start the Jupyter server in a separate process"""
        # Kill any existing Jupyter processes
        os.system('pkill -f jupyter')

        self.process = multiprocessing.Process(
            target=run_jupyter_server,
            args=(self.notebook_dir, self.jupyter_port)
        )
        self.process.start()
        time.sleep(5)  # Give more time for the server to start

    def stop_jupyter_server(self):
        """Stop the Jupyter server"""
        if self.process:
            self.process.terminate()
            self.process.join()
            os.system('pkill -f jupyter')


def create_app():
    # Create the Dash application
    app = dash.Dash(
        __name__,
        meta_tags=[
            {"name": "Content-Security-Policy",
             "content": "frame-ancestors 'self' http://localhost:* http://127.0.0.1:*"}
        ]
    )

    # Initialize and start Jupyter server
    jupyter_integration = JupyterDashIntegration()
    jupyter_integration.start_jupyter_server()

    # Define the layout
    app.layout = html.Div([
        html.H1("Interactive Jupyter Notebook in Dash"),
        html.Hr(),
        html.Iframe(
            # Use JupyterLab interface
            src="http://127.0.0.1:8888/lab",
            style={
                'width': '100%',
                'height': '800px',
                'border': 'none'
            },
            sandbox="allow-same-origin allow-scripts allow-popups allow-forms allow-top-navigation"
        )
    ])

    # Add required headers for iframe communication
    @app.server.after_request
    def after_request(response):
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,PUT,POST,DELETE,OPTIONS',
            'Content-Security-Policy': "frame-ancestors 'self' http://localhost:* http://127.0.0.1:*"
        }
        for header, value in headers.items():
            response.headers[header] = value
        return response

    return app, jupyter_integration


if __name__ == '__main__':
    # Enable multiprocessing for MacOS
    multiprocessing.freeze_support()

    # Create notebook directory if it doesn't exist
    if not os.path.exists('jupyter'):
        os.makedirs('jupyter')

    # Copy the notebook to the jupyter directory
    notebook_source = 'notebook.ipynb'
    notebook_dest = os.path.join('jupyter', 'notebook.ipynb')
    if os.path.exists(notebook_source):
        shutil.copy2(notebook_source, notebook_dest)
    else:
        # Create a sample notebook if source doesn't exist
        with open(notebook_dest, 'w') as f:
            f.write('''{
             "cells": [
              {
               "cell_type": "markdown",
               "metadata": {},
               "source": [
                "# Welcome to Jupyter Notebook\\n",
                "This is a sample notebook."
               ]
              },
              {
               "cell_type": "code",
               "execution_count": null,
               "metadata": {},
               "outputs": [],
               "source": [
                "print(\\"Hello, World!\\")"
               ]
              }
             ],
             "metadata": {
              "kernelspec": {
               "display_name": "Python 3",
               "language": "python",
               "name": "python3"
              }
             },
             "nbformat": 4,
             "nbformat_minor": 4
            }''')

    # Kill any existing Jupyter processes
    os.system('pkill -f jupyter')

    # Create and start the application
    app, jupyter_integration = create_app()

    try:
        print("Starting Dash server on http://localhost:8050")
        print("Jupyter Lab should be available at http://127.0.0.1:8888/lab")
        # Start the Dash server
        app.run_server(debug=True, port=8050, host='0.0.0.0')
    except Exception as e:
        print(f"Error starting Dash server: {str(e)}")
        raise
    finally:
        # Ensure Jupyter server is properly stopped
        jupyter_integration.stop_jupyter_server()