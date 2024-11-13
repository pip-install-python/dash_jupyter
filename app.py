from dash import Dash, html, dcc, Input, Output, State
import dash
import dash_bootstrap_components as dbc
import leafmap.foliumap as leafmap
import tempfile
import os
import base64
from pathlib import Path


class DashLeafmap:
    def __init__(self):
        self.app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.temp_dir = tempfile.mkdtemp()

        # Initialize the layout
        self.app.layout = dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H3("Leafmap Dashboard"),
                    dbc.Card([
                        dbc.CardHeader("Map Controls"),
                        dbc.CardBody([
                            dbc.Button("Add Basemap", id="basemap-button", className="me-2"),
                            dbc.Button("Split Map", id="split-map-button", className="me-2"),
                            dbc.Button("Add GeoJSON", id="geojson-button", className="me-2"),
                            dbc.Button("Add WMS", id="wms-button", className="me-2"),
                            dcc.Upload(
                                id='upload-data',
                                children=dbc.Button('Upload File'),
                                multiple=False,
                                className="me-2"
                            ),
                        ])
                    ], className="mb-3"),

                    # Basemap Modal
                    dbc.Modal([
                        dbc.ModalHeader("Select Basemap"),
                        dbc.ModalBody([
                            dcc.Dropdown(
                                id='basemap-dropdown',
                                options=[
                                    {'label': name, 'value': name}
                                    for name in leafmap.basemaps.keys()
                                ],
                                value='OpenStreetMap'
                            )
                        ]),
                        dbc.ModalFooter(
                            dbc.Button("Apply", id="apply-basemap", className="ms-auto")
                        ),
                    ], id="basemap-modal", is_open=False),

                    # Split Map Modal
                    dbc.Modal([
                        dbc.ModalHeader("Configure Split Map"),
                        dbc.ModalBody([
                            html.Label("Left Layer"),
                            dcc.Dropdown(
                                id='left-layer-dropdown',
                                options=[
                                    {'label': name, 'value': name}
                                    for name in leafmap.basemaps.keys()
                                ],
                                value='TERRAIN'
                            ),
                            html.Br(),
                            html.Label("Right Layer"),
                            dcc.Dropdown(
                                id='right-layer-dropdown',
                                options=[
                                    {'label': name, 'value': name}
                                    for name in leafmap.basemaps.keys()
                                ],
                                value='OpenTopoMap'
                            ),
                        ]),
                        dbc.ModalFooter(
                            dbc.Button("Apply", id="apply-split", className="ms-auto")
                        ),
                    ], id="split-map-modal", is_open=False),

                    # Map IFrame
                    html.Iframe(
                        id='map-iframe',
                        srcDoc='',
                        style={'width': '100%', 'height': '600px'},
                    ),
                ], width=12)
            ])
        ], fluid=True)

        self._setup_callbacks()
        self._initialize_map()

    def _initialize_map(self):
        """Initialize the map and save it to HTML"""
        m = leafmap.Map()
        self.map_file = os.path.join(self.temp_dir, "map.html")
        m.to_html(self.map_file)

    def _setup_callbacks(self):
        @self.app.callback(
            [Output("basemap-modal", "is_open"),
             Output("split-map-modal", "is_open")],
            [Input("basemap-button", "n_clicks"),
             Input("split-map-button", "n_clicks")],
            [State("basemap-modal", "is_open"),
             State("split-map-modal", "is_open")]
        )
        def toggle_modals(basemap_clicks, split_clicks, basemap_open, split_open):
            ctx = dash.callback_context
            if not ctx.triggered:
                return basemap_open, split_open

            button_id = ctx.triggered[0]["prop_id"].split(".")[0]

            if button_id == "basemap-button":
                return not basemap_open, False
            elif button_id == "split-map-button":
                return False, not split_open
            return basemap_open, split_open

        @self.app.callback(
            Output('map-iframe', 'srcDoc'),
            [Input('apply-basemap', 'n_clicks'),
             Input('apply-split', 'n_clicks'),
             Input('upload-data', 'contents')],
            [State('basemap-dropdown', 'value'),
             State('left-layer-dropdown', 'value'),
             State('right-layer-dropdown', 'value'),
             State('upload-data', 'filename')]
        )
        def update_map(basemap_clicks, split_clicks, contents,
                       basemap, left_layer, right_layer, filename):

            ctx = dash.callback_context
            if not ctx.triggered:
                return dash.no_update

            trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

            m = leafmap.Map()

            if trigger_id == 'apply-basemap' and basemap_clicks:
                m.add_basemap(basemap)

            elif trigger_id == 'apply-split' and split_clicks:
                # Create a new map with split panels
                try:
                    m.split_map(
                        left_layer=left_layer,
                        right_layer=right_layer
                    )
                except Exception as e:
                    print(f"Error creating split map: {e}")
                    # Fallback to regular map if split fails
                    m = leafmap.Map()
                    m.add_basemap(left_layer)

            elif trigger_id == 'upload-data' and contents:
                content_type, content_string = contents.split(',')
                decoded = base64.b64decode(content_string)

                if filename.endswith('.geojson'):
                    with tempfile.NamedTemporaryFile(suffix='.geojson', delete=False) as tmp:
                        tmp.write(decoded)
                        tmp.flush()
                        m.add_geojson(tmp.name, layer_name=Path(filename).stem)

                elif filename.endswith('.shp'):
                    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
                        tmp.write(decoded)
                        tmp.flush()
                        m.add_shp(tmp.name, layer_name=Path(filename).stem)

            # Save and return the map
            map_html = os.path.join(self.temp_dir, "map.html")
            m.to_html(map_html)
            with open(map_html, 'r') as f:
                return f.read()

    def run_server(self, **kwargs):
        self.app.run_server(**kwargs)


# Usage example
if __name__ == '__main__':
    app = DashLeafmap()
    app.run_server(debug=True)