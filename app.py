"""
Plane — complex function visualizer, Python backend
=====================================================

w = f(z), where z = x + i*a (input) and w = y + i*b (output).

The frontend (templates/index.html) only collects: the equation, the
rotation matrix [m°, n°], and which of {x, y, im(a), im(b)} should be
used as the color channel. Every number is crunched here — numpy
builds the grid and evaluates f(z), matplotlib renders and colors the
3D surface — and the result is shipped back to the browser as a PNG.

Run:
    pip install flask numpy matplotlib
    python app.py
Then open http://127.0.0.1:5000
"""

import base64
import io
import re

import matplotlib
matplotlib.use("Agg")  # headless rendering — no display needed on the server
import matplotlib.pyplot as plt
import numpy as np
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

N = 60
RANGE = 2.0
CLIP = RANGE * 6
CANONICAL_ORDER = ["x", "y", "a", "b"]
LABELS = {
    "x": "x  (Re input)", "y": "y  (Re output)",
    "a": "im(a)  (Im input)", "b": "im(b)  (Im output)",
}
CMAP = plt.get_cmap("viridis")

# Names allowed inside an equation, e.g. "sin(z)**2 + exp(1/z)"
SAFE_NAMES = {
    "sin": np.sin, "cos": np.cos, "tan": np.tan,
    "sinh": np.sinh, "cosh": np.cosh, "tanh": np.tanh,
    "exp": np.exp, "log": np.log, "sqrt": np.sqrt,
    "abs": np.abs, "conj": np.conj,
    "pi": np.pi, "e": np.e, "j": 1j,
}


def compile_equation(text):
    """Turn a user-supplied string like 'z^2' or 'sin(z)/z' into a
    numpy-vectorized function of z. Only whitelisted names are exposed;
    everything else is rejected before eval ever runs."""
    text = (text or "").strip()
    if not text:
        raise ValueError("Enter an equation.")

    expr = text.replace("^", "**")

    identifiers = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr))
    allowed = set(SAFE_NAMES) | {"z"}
    unknown = identifiers - allowed
    if unknown:
        raise ValueError(f"Unknown name(s) in equation: {', '.join(sorted(unknown))}")

    code = compile(expr, "<equation>", "eval")

    def f(z):
        return eval(code, {"__builtins__": {}}, {**SAFE_NAMES, "z": z})

    # smoke-test it before trusting it on the full grid
    try:
        f(np.complex128(1.0 + 1.0j))
    except Exception as e:
        raise ValueError(f"Couldn't evaluate that equation ({e}).")

    return f


def compute_fields(equation_text):
    f = compile_equation(equation_text)

    lin = np.linspace(-RANGE, RANGE, N)
    X, A = np.meshgrid(lin, lin)
    Z = X + 1j * A

    with np.errstate(all="ignore"):
        W = f(Z)
        W = np.asarray(W, dtype=np.complex128)
        W = np.where(np.isfinite(W), W, 0)

    Y = np.clip(np.real(W), -CLIP, CLIP)
    B = np.clip(np.imag(W), -CLIP, CLIP)

    return {"x": X, "y": Y, "a": A, "b": B}


def render_png(fields, color_key, m, n):
    spatial_keys = [k for k in CANONICAL_ORDER if k != color_key]
    sx, sy, sz = (fields[k] for k in spatial_keys)
    cfield = fields[color_key]

    norm = plt.Normalize(vmin=np.nanmin(cfield), vmax=np.nanmax(cfield))
    facecolors = CMAP(norm(cfield))

    fig = plt.figure(figsize=(6, 6), dpi=140)
    ax = fig.add_subplot(111, projection="3d")
    fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)

    ax.plot_surface(
        sx, sy, sz,
        facecolors=facecolors,
        rstride=1, cstride=1,
        linewidth=0, antialiased=False, shade=False,
    )
    ax.set_box_aspect(None, zoom=1.15)
    ax.view_init(elev=n, azim=m)
    ax.set_xlabel(LABELS[spatial_keys[0]], fontsize=8)
    ax.set_ylabel(LABELS[spatial_keys[1]], fontsize=8)
    ax.set_zlabel(LABELS[spatial_keys[2]], fontsize=8)
    ax.tick_params(labelsize=7)
    ax.set_facecolor("#FFFBFE")
    fig.patch.set_facecolor("#FFFBFE")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/render", methods=["POST"])
def api_render():
    payload = request.get_json(force=True, silent=True) or {}
    equation = payload.get("equation", "z**2")
    color_key = payload.get("color", "b")
    try:
        m = float(payload.get("m", 45))
        n = float(payload.get("n", 45))
    except (TypeError, ValueError):
        return jsonify({"error": "Rotation values must be numbers."}), 400

    if color_key not in CANONICAL_ORDER:
        return jsonify({"error": "Invalid color plane."}), 400
    n = max(-90.0, min(90.0, n))
    m = ((m + 180) % 360) - 180

    try:
        fields = compute_fields(equation)
        image_b64 = render_png(fields, color_key, m, n)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Render failed: {e}"}), 500

    return jsonify({"image": f"data:image/png;base64,{image_b64}", "m": m, "n": n})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
