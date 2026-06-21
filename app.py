import json
import os
import secrets
import uuid
import warnings
from datetime import datetime
from pathlib import Path

from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import (Flask, abort, flash, redirect, render_template, request,
                   url_for)
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from markupsafe import Markup
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from wtforms import PasswordField, SelectField, StringField, SubmitField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def _load_config():
    """Read config.json. Creates file with defaults if missing."""
    defaults = {
        "auth_mode": 3,
        "allow_registration": True,
        "_comment": [
            "Authentication mode:",
            "  1 = Email/password only (register + login forms)",
            "  2 = External OAuth only (Google + GitHub)",
            "  3 = Both email/password and OAuth (default)",
            "",
            "allow_registration:",
            "  false = New registrations are disabled (existing users can still log in).",
            "  true  = Anyone can register (default).",
        ],
    }
    if not os.path.exists(_CONFIG_PATH):
        with open(_CONFIG_PATH, "w") as f:
            json.dump(defaults, f, indent=4)
        return defaults
    try:
        with open(_CONFIG_PATH) as f:
            data = json.load(f)
        mode = data.get("auth_mode", 3)
        if mode not in (1, 2, 3):
            mode = 3
        data["auth_mode"] = mode
        data["allow_registration"] = data.get("allow_registration", True)
        return data
    except (json.JSONDecodeError, OSError):
        return defaults


_CONFIG = _load_config()
AUTH_MODE = _CONFIG["auth_mode"]
ALLOW_REGISTRATION = _CONFIG["allow_registration"]

# Roles file — maps email → role (e.g. "admin@example.com": "admin")
# Lives next to config.json so the admin can edit it directly.
_ROLES_PATH = None  # set after DATABASE_DIR is resolved

def _load_roles():
    """Read the roles file and return a dict of email → role."""
    if not os.path.exists(_ROLES_PATH):
        return {}
    try:
        with open(_ROLES_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

_PUBLIC_URL = os.getenv("PUBLIC_URL", "").rstrip("/")

def _external_url(endpoint, **values):
    """Generate an absolute URL, using PUBLIC_URL as the base if set.
    This avoids Host-header dependency — critical behind Cloudflare Tunnel."""
    path = url_for(endpoint, **values)
    if _PUBLIC_URL:
        return f"{_PUBLIC_URL}{path}"
    return url_for(endpoint, _external=True, **values)

# ---------------------------------------------------------------------------
# App & Database Setup
# ---------------------------------------------------------------------------
app = Flask(__name__)

# Trust Cloudflare Tunnel's forwarded headers (X-Forwarded-Proto, X-Forwarded-Host)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# SECRET_KEY — auto-generate if not set (warns so you know to persist it)
_secret = os.getenv("SECRET_KEY")
if not _secret:
    _secret = secrets.token_hex(32)
    warnings.warn(
        "No SECRET_KEY set. Auto-generated one-time key — sessions will be "
        "invalidated on restart. Set the SECRET_KEY environment variable for permanence.",
        RuntimeWarning,
    )
app.config["SECRET_KEY"] = _secret

# Database — path configurable via env var (for Docker volume mounts)
_db_dir = os.getenv("DATABASE_DIR", os.path.join(app.instance_path))
os.makedirs(_db_dir, exist_ok=True)
_db_path = os.path.join(_db_dir, "snippets.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{_db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Roles file lives alongside the database for Docker volume persistence
_ROLES_PATH = os.path.join(_db_dir, "roles.json")

# OAuth absolute callback URLs
app.config["PREFERRED_URL_SCHEME"] = os.getenv("PREFERRED_URL_SCHEME", "https")

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ---------------------------------------------------------------------------
# OAuth (loaded only in modes 2 & 3)
# ---------------------------------------------------------------------------
oauth = OAuth(app)

_USE_OAUTH = AUTH_MODE in (2, 3)

if _USE_OAUTH:
    oauth.register(
        name="google",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    oauth.register(
        name="github",
        client_id=os.getenv("GITHUB_CLIENT_ID"),
        client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "user:email"},
    )


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=True)  # null for OAuth-only users
    avatar_url = db.Column(db.String(500), default="")
    oauth_provider = db.Column(db.String(20))   # "google" or "github"
    oauth_id = db.Column(db.String(200))         # provider's user id
    role = db.Column(db.String(20), default="user")  # user, admin, moderator, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    snippets = db.relationship("Snippet", back_populates="author", lazy="dynamic")

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)


def _sync_user_role(user):
    """Look up the user's email in roles.json and update their role column.
    If no role is defined, default to 'user'."""
    roles = _load_roles()
    role = roles.get(user.email, "user")
    if user.role != role:
        user.role = role
        db.session.commit()
    return role


class Snippet(db.Model):
    __tablename__ = "snippets"

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False)
    code = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(50), nullable=False, default="text")
    tags = db.Column(db.String(500), default="")
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    author = db.relationship("User", back_populates="snippets")

    def tag_list(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    def highlighted_code(self):
        try:
            lexer = get_lexer_by_name(self.language, stripall=True)
        except Exception:
            try:
                lexer = guess_lexer(self.code)
            except Exception:
                lexer = get_lexer_by_name("text")
        formatter = HtmlFormatter(style="monokai", lineseparator="\n")
        raw = highlight(self.code, lexer, formatter)
        return Markup(raw)

    def css_styles(self):
        return Markup(HtmlFormatter(style="monokai").get_style_defs(".highlight"))


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------
LANGUAGES = [
    ("text", "Plain Text"),
    ("python", "Python"),
    ("javascript", "JavaScript"),
    ("typescript", "TypeScript"),
    ("html", "HTML"),
    ("css", "CSS"),
    ("sql", "SQL"),
    ("java", "Java"),
    ("cpp", "C++"),
    ("c", "C"),
    ("csharp", "C#"),
    ("go", "Go"),
    ("rust", "Rust"),
    ("ruby", "Ruby"),
    ("php", "PHP"),
    ("swift", "Swift"),
    ("kotlin", "Kotlin"),
    ("bash", "Bash"),
    ("yaml", "YAML"),
    ("json", "JSON"),
    ("markdown", "Markdown"),
]


# ---------------------------------------------------------------------------
# Auth forms (used in modes 1 & 3)
# ---------------------------------------------------------------------------
_USE_EMAIL_AUTH = AUTH_MODE in (1, 3)

if _USE_EMAIL_AUTH:

    class RegisterForm(FlaskForm):
        username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
        email = StringField("Email", validators=[DataRequired(), Email()])
        password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
        confirm = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
        submit = SubmitField("Register")

        def validate_username(self, field):
            if User.query.filter_by(username=field.data).first():
                raise ValidationError("Username already taken.")

        def validate_email(self, field):
            if User.query.filter_by(email=field.data).first():
                raise ValidationError("Email already registered.")

    class LoginForm(FlaskForm):
        email = StringField("Email", validators=[DataRequired(), Email()])
        password = PasswordField("Password", validators=[DataRequired()])
        submit = SubmitField("Log In")


# ---------------------------------------------------------------------------
# Snippet form
# ---------------------------------------------------------------------------
class SnippetForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=200)])
    code = TextAreaField("Code", validators=[DataRequired()])
    language = SelectField("Language", choices=LANGUAGES, default="python")
    tags = StringField("Tags (comma-separated)", validators=[Length(max=500)])
    is_public = BooleanField("Make this snippet public (anyone with the link can view)")
    submit = SubmitField("Save Snippet")


# ---------------------------------------------------------------------------
# Login Manager
# ---------------------------------------------------------------------------
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ---------------------------------------------------------------------------
# Context processor — inject auth_mode into all templates
# ---------------------------------------------------------------------------
@app.context_processor
def inject_globals():
    return {
        "auth_mode": AUTH_MODE,
        "use_oauth": _USE_OAUTH,
        "use_email_auth": _USE_EMAIL_AUTH,
        "allow_registration": ALLOW_REGISTRATION,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _find_or_create_user(email, username, avatar_url, provider, oauth_id):
    user = User.query.filter_by(email=email).first()
    if user:
        # Update profile info in case it changed on the provider side
        user.username = username
        user.avatar_url = avatar_url or user.avatar_url
        user.oauth_provider = provider
        user.oauth_id = oauth_id
        db.session.commit()
        # Sync role from roles.json
        _sync_user_role(user)
        return user

    # Check if registration is allowed
    if not ALLOW_REGISTRATION:
        return None

    # Handle duplicate usernames by appending a suffix
    base_username = username
    suffix = 1
    while User.query.filter_by(username=username).first():
        username = f"{base_username}{suffix}"
        suffix += 1

    user = User(
        username=username,
        email=email,
        avatar_url=avatar_url or "",
        oauth_provider=provider,
        oauth_id=oauth_id,
        role="user",
    )
    db.session.add(user)
    db.session.commit()
    # Apply role from roles.json (overrides default "user" if present)
    _sync_user_role(user)
    return user


# ---------------------------------------------------------------------------
# Auth Routes
# ---------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    # Email/password form (modes 1 & 3)
    login_form = None
    if _USE_EMAIL_AUTH:
        login_form = LoginForm()
        if login_form.validate_on_submit():
            user = User.query.filter_by(email=login_form.email.data).first()
            if user and user.check_password(login_form.password.data):
                _sync_user_role(user)
                login_user(user)
                flash(f"Welcome back, {user.username}!", "success")
                return redirect(url_for("dashboard"))
            flash("Invalid email or password.", "danger")

    return render_template("login.html", form=login_form)


# --- Email/password routes (modes 1 & 3) ---
if _USE_EMAIL_AUTH:

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if not ALLOW_REGISTRATION:
            flash("Registration is currently disabled.", "danger")
            return redirect(url_for("login"))
        form = RegisterForm()
        if form.validate_on_submit():
            user = User(
                username=form.username.data,
                email=form.email.data,
                role="user",
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            # Apply role from roles.json (overrides default "user" if present)
            _sync_user_role(user)
            login_user(user)
            flash("Account created! Welcome to SnippetVault.", "success")
            return redirect(url_for("dashboard"))
        return render_template("register.html", form=form)


# --- OAuth routes (modes 2 & 3) ---
if _USE_OAUTH:

    @app.route("/login/google")
    def login_google():
        redirect_uri = _external_url("authorize_google")
        return oauth.google.authorize_redirect(redirect_uri)

    @app.route("/login/google/authorize")
    def authorize_google():
        token = oauth.google.authorize_access_token()
        userinfo = token.get("userinfo") or oauth.google.parse_id_token(token)
        email = userinfo.get("email")
        if not email:
            flash("Google did not return an email address.", "danger")
            return redirect(url_for("login"))

        user = _find_or_create_user(
            email=email,
            username=userinfo.get("name", email.split("@")[0]),
            avatar_url=userinfo.get("picture", ""),
            provider="google",
            oauth_id=userinfo.get("sub", email),
        )
        if not user:
            flash("Registration is currently disabled.", "danger")
            return redirect(url_for("login"))
        login_user(user, remember=True)
        flash(f"Welcome, {user.username}!", "success")
        return redirect(url_for("dashboard"))

    @app.route("/login/github")
    def login_github():
        redirect_uri = _external_url("authorize_github")
        return oauth.github.authorize_redirect(redirect_uri)

    @app.route("/login/github/authorize")
    def authorize_github():
        token = oauth.github.authorize_access_token()
        headers = {"Authorization": f"Bearer {token['access_token']}"}

        resp = oauth.github.get("user", headers=headers)
        gh_user = resp.json()
        github_id = str(gh_user["id"])

        email = gh_user.get("email")
        if not email:
            email_resp = oauth.github.get("user/emails", headers=headers)
            emails = email_resp.json()
            if emails:
                email = next((e["email"] for e in emails if e.get("primary")), emails[0]["email"])

        if not email:
            flash("GitHub did not return an email address. Make sure you have a public email set.", "danger")
            return redirect(url_for("login"))

        user = _find_or_create_user(
            email=email,
            username=gh_user.get("login", email.split("@")[0]),
            avatar_url=gh_user.get("avatar_url", ""),
            provider="github",
            oauth_id=github_id,
        )
        if not user:
            flash("Registration is currently disabled.", "danger")
            return redirect(url_for("login"))
        login_user(user, remember=True)
        flash(f"Welcome, {user.username}!", "success")
        return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# Standard Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    recent = Snippet.query.filter_by(is_public=True).order_by(Snippet.created_at.desc()).limit(10).all()
    return render_template("index.html", recent=recent)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    tag_filter = request.args.get("tag", "").strip()

    query = Snippet.query.filter_by(author_id=current_user.id)

    if q:
        query = query.filter(
            db.or_(
                Snippet.title.ilike(f"%{q}%"),
                Snippet.code.ilike(f"%{q}%"),
                Snippet.tags.ilike(f"%{q}%"),
            )
        )
    if tag_filter:
        query = query.filter(Snippet.tags.ilike(f"%{tag_filter}%"))

    snippets = query.order_by(Snippet.updated_at.desc()).paginate(
        page=page, per_page=15, error_out=False
    )

    all_user_snippets = Snippet.query.filter_by(author_id=current_user.id).all()
    all_tags = sorted(set(
        t.strip() for s in all_user_snippets for t in s.tags.split(",") if t.strip()
    ))

    return render_template(
        "dashboard.html",
        snippets=snippets,
        query=q,
        tag_filter=tag_filter,
        all_tags=all_tags,
    )


@app.route("/snippet/new", methods=["GET", "POST"])
@login_required
def create_snippet():
    form = SnippetForm()
    if form.validate_on_submit():
        snippet = Snippet(
            title=form.title.data,
            code=form.code.data,
            language=form.language.data,
            tags=form.tags.data,
            is_public=form.is_public.data,
            author=current_user,
        )
        db.session.add(snippet)
        db.session.commit()
        flash("Snippet saved!", "success")
        return redirect(url_for("view_snippet", uuid=snippet.uuid))
    return render_template("create_snippet.html", form=form, mode="create")


@app.route("/snippet/<uuid>")
def view_snippet(uuid):
    snippet = Snippet.query.filter_by(uuid=uuid).first_or_404()
    if not snippet.is_public and (
        not current_user.is_authenticated or current_user.id != snippet.author_id
    ):
        abort(403)
    return render_template("snippet.html", snippet=snippet)


@app.route("/snippet/<uuid>/edit", methods=["GET", "POST"])
@login_required
def edit_snippet(uuid):
    snippet = Snippet.query.filter_by(uuid=uuid).first_or_404()
    if snippet.author_id != current_user.id:
        abort(403)
    form = SnippetForm(obj=snippet)
    if form.validate_on_submit():
        snippet.title = form.title.data
        snippet.code = form.code.data
        snippet.language = form.language.data
        snippet.tags = form.tags.data
        snippet.is_public = form.is_public.data
        db.session.commit()
        flash("Snippet updated!", "success")
        return redirect(url_for("view_snippet", uuid=snippet.uuid))
    return render_template("create_snippet.html", form=form, snippet=snippet, mode="edit")


@app.route("/snippet/<uuid>/delete", methods=["GET"])
@login_required
def delete_snippet(uuid):
    snippet = Snippet.query.filter_by(uuid=uuid).first_or_404()
    if snippet.author_id != current_user.id:
        abort(403)
    db.session.delete(snippet)
    db.session.commit()
    flash("Snippet deleted.", "info")
    return redirect(url_for("dashboard"))


@app.route("/explore")
def explore():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    lang = request.args.get("lang", "").strip()
    tag = request.args.get("tag", "").strip()

    query = Snippet.query.filter_by(is_public=True)

    if q:
        query = query.filter(
            db.or_(
                Snippet.title.ilike(f"%{q}%"),
                Snippet.code.ilike(f"%{q}%"),
                Snippet.tags.ilike(f"%{tag}%"),
            )
        )
    if lang:
        query = query.filter(Snippet.language == lang)
    if tag:
        query = query.filter(Snippet.tags.ilike(f"%{tag}%"))

    snippets = query.order_by(Snippet.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template("explore.html", snippets=snippets, query=q, lang=lang, tag=tag, languages=LANGUAGES)


@app.route("/user/<username>")
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    snippets = (
        Snippet.query.filter_by(author_id=user.id, is_public=True)
        .order_by(Snippet.created_at.desc())
        .all()
    )
    return render_template("user_profile.html", profile_user=user, snippets=snippets)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.route("/health")
def health():
    return {"status": "ok"}, 200


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", code=403, message="You don't have permission to do that."), 403


@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="Page not found."), 404


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def init_db():
    """Create tables, add missing columns, and enable WAL mode."""
    with app.app_context():
        db.create_all()
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        columns = {c["name"] for c in inspector.get_columns("users")}
        # Migrate: add password_hash column if missing (upgrade path for existing DBs)
        if "password_hash" not in columns:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(200)"))
                conn.commit()
        # Migrate: add role column if missing
        if "role" not in columns:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user'"))
                conn.commit()
        # Enable WAL mode for SQLite (better concurrent reads)
        with db.engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.commit()
        # Sync roles from roles.json to all existing users
        roles = _load_roles()
        for email, role in roles.items():
            user = User.query.filter_by(email=email).first()
            if user and user.role != role:
                user.role = role
        db.session.commit()


if __name__ == "__main__":
    init_db()

    # Use Waitress in production (cross-platform WSGI server)
    _port = int(os.getenv("PORT", "5001"))
    _host = os.getenv("HOST", "0.0.0.0")

    if os.getenv("WAITRESS", "").lower() in ("1", "true", "yes"):
        from waitress import serve
        print(f"Starting Waitress on {_host}:{_port}")
        serve(app, host=_host, port=_port)
    else:
        print(f"Starting Flask dev server on {_host}:{_port}")
        app.run(host=_host, port=_port, debug=True)
