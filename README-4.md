# Plane — complex function visualizer

A Material You–styled GUI where every number is crunched by a Python
backend. The browser only collects input (equation, rotation matrix,
color plane) and displays the PNG the server renders.

```
plane_app/
├── app.py                 Flask app + numpy field computation + matplotlib rendering
├── templates/
│   └── index.html         GUI (fetch()'s the backend, no client-side math)
└── requirements.txt
```

## Run it

```
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000** in a browser.

## How it works

1. `w = f(z)` where `z = x + i·a` is the input and `w = y + i·b` is the output.
2. The frontend sends `{equation, m, n, color}` to `POST /api/render`.
3. `app.py` builds the `x, a` grid with numpy, evaluates the equation
   (`z**2`, `sin(z)/z`, `1/z`, ... — only whitelisted names are allowed,
   everything else is rejected before it ever reaches `eval`), and hands
   the four real fields (x, y, im(a), im(b)) to matplotlib.
4. matplotlib renders the chosen three as the 3D axes and the fourth as
   color, rotated by `Rotation_Matrix = [m°, n°]` (m = azimuth, n =
   elevation), and returns a PNG as base64.
5. The image fills the output box in the browser. Dragging a rotation
   slider or switching the color tab re-requests a fresh render once an
   image already exists; the box starts empty until you click **Generate**.
