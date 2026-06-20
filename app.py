"""
MovieHub v6.1 - ВСЁ ИСПРАВЛЕНО
pip install flask flask-sqlalchemy flask-login flask-socketio
"""

from flask import Flask, request, redirect, url_for, flash, jsonify, get_flashed_messages
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_socketio import SocketIO, send, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moviehub-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///moviehub_final.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ==================== Модели ====================
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    comments = db.relationship('Comment', backref='author', lazy=True, cascade='all, delete-orphan')

class Movie(db.Model):
    __tablename__ = 'movie'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    genre = db.Column(db.String(100), nullable=False)
    poster_url = db.Column(db.String(500))
    trailer_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    comments = db.relationship('Comment', backref='movie', lazy=True, cascade='all, delete-orphan')
    platforms = db.relationship('Platform', backref='movie', lazy=True, cascade='all, delete-orphan')

class Comment(db.Model):
    __tablename__ = 'comment'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False)

class Rating(db.Model):
    __tablename__ = 'rating'
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'movie_id'),)

class Platform(db.Model):
    __tablename__ = 'platform'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    is_free = db.Column(db.Boolean, default=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ==================== HTML ====================
def base_page(title, body, scripts=""):
    nav = ""
    if current_user.is_authenticated:
        admin_btn = '<a href="/admin" class="btn btn-outline-warning btn-sm me-2">⚙️ Админ</a>' if current_user.is_admin else ''
        nav = f'''<span class="navbar-text me-3 text-white">👤 {current_user.username}</span>{admin_btn}<a href="/logout" class="btn btn-outline-light btn-sm">Выйти</a>'''
    else:
        nav = '''<a href="/login" class="btn btn-outline-light btn-sm me-2">Войти</a><a href="/register" class="btn btn-outline-success btn-sm">Регистрация</a>'''
    
    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{title} - MovieHub</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    <style>
        body{{background:#0d1117;color:#e6edf3;font-family:'Segoe UI',Arial,sans-serif}}
        .navbar{{background:#161b22!important;border-bottom:1px solid #30363d;padding:10px 0}}
        .navbar-brand{{color:#58a6ff!important;font-weight:bold;font-size:24px}}
        .card{{background:#1c2333;border:1px solid #30363d;border-radius:10px;overflow:hidden}}
        .card-title{{color:#ffd700;font-weight:bold;font-size:20px}}
        .card-text{{color:#c9d1d9}}
        .card-body{{padding:20px}}
        .btn-primary{{background:#238636;border:none;color:white}}
        .btn-primary:hover{{background:#2ea043}}
        .btn-warning{{background:#d2991d;border:none;color:#000}}
        .btn-danger{{background:#da3633;border:none}}
        .btn-success{{background:#238636;border:none}}
        .btn-outline-primary{{border-color:#58a6ff;color:#58a6ff}}
        .btn-outline-primary:hover{{background:#58a6ff;color:#000}}
        .btn-outline-success{{border-color:#3fb950;color:#3fb950}}
        .btn-outline-light{{border-color:#c9d1d9;color:#c9d1d9}}
        .btn-outline-warning{{border-color:#ffd700;color:#ffd700}}
        .form-control{{background:#0d1117;border:1px solid #30363d;color:#e6edf3}}
        .form-control:focus{{border-color:#58a6ff;box-shadow:0 0 10px rgba(88,166,255,0.3)}}
        .chat-box{{height:400px;overflow-y:auto;background:#0d1117;border:1px solid #30363d;border-radius:10px;padding:15px}}
        .chat-msg{{background:#1a2332;border-left:3px solid #58a6ff;padding:12px;margin:8px 0;border-radius:5px;color:#e6edf3}}
        .movie-card{{transition:all .3s;cursor:pointer}}
        .movie-card:hover{{transform:translateY(-10px);box-shadow:0 10px 30px rgba(88,166,255,0.3)}}
        .movie-card img{{height:300px;object-fit:cover}}
        .hero{{background:linear-gradient(135deg,#238636,#1f6feb);border-radius:15px;padding:60px;margin-bottom:30px}}
        .hero h1{{color:#fff;font-size:48px;font-weight:bold}}
        .genre-box{{background:#1c2333;border:1px solid #30363d;border-radius:10px;padding:20px;transition:all .3s}}
        .genre-box:hover{{background:#243044;border-color:#58a6ff;transform:translateY(-5px)}}
        .genre-box h5{{color:#58a6ff;font-weight:bold}}
        .star{{color:#ffd700;cursor:pointer;font-size:28px}}
        .star:hover{{transform:scale(1.3)}}
        .alert{{background:#1c2333;border:1px solid #30363d;border-radius:10px}}
        .table{{color:#e6edf3}}
        .table thead th{{color:#58a6ff;border-bottom:2px solid #30363d}}
        .table td{{border-bottom:1px solid #30363d}}
        h1,h2,h3,h4,h5,h6{{color:#e6edf3;font-weight:bold}}
        p{{color:#c9d1d9;line-height:1.6}}
        a{{color:#58a6ff;text-decoration:none}}
        label{{color:#c9d1d9;font-weight:bold}}
        small{{color:#8b949e}}
        strong{{color:#e6edf3}}
        footer{{background:#161b22;border-top:1px solid #30363d;color:#8b949e}}
        .section-title{{border-bottom:2px solid #30363d;padding-bottom:10px;margin-bottom:20px}}
        .movie-title{{color:#ffd700!important}}
        img{{border-radius:10px}}
        ::-webkit-scrollbar{{width:10px}}
        ::-webkit-scrollbar-track{{background:#0d1117}}
        ::-webkit-scrollbar-thumb{{background:#30363d;border-radius:5px}}
    </style>
</head>
<body>
    <nav class="navbar navbar-dark"><div class="container"><a class="navbar-brand" href="/">🎬 MovieHub</a><div class="d-flex align-items-center">{nav}</div></div></nav>
    <div class="container mt-4">{body}</div>
    <footer class="text-center py-4 mt-5"><p class="mb-0">© 2024 MovieHub</p></footer>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    {scripts}
</body>
</html>'''

# ==================== Главная ====================
@app.route('/')
def index():
    search = request.args.get('search', '').strip()
    movies = Movie.query.order_by(Movie.created_at.desc()).all()
    if search:
        movies = [m for m in movies if search.lower() in m.title.lower()]
    
    genres = db.session.query(Movie.genre).distinct().all()
    gb = ''.join([f'<div class="col-md-3 mb-3"><a href="/genre/{g[0]}" class="text-decoration-none"><div class="genre-box text-center"><h5>📁 {g[0]}</h5><p class="mb-0">{Movie.query.filter_by(genre=g[0]).count()} фильмов</p></div></a></div>' for g in sorted(genres)])
    
    mc = ''.join([f'<div class="col-md-4 mb-4"><div class="card movie-card h-100"><img src="{m.poster_url or "https://via.placeholder.com/300x450"}" class="card-img-top"><div class="card-body"><h5 class="card-title">{m.title}</h5><span class="badge bg-primary mb-2">{m.genre}</span><p class="card-text">{m.description[:100]}...</p><a href="/movie/{m.id}" class="btn btn-outline-primary btn-sm">Подробнее</a></div></div></div>' for m in movies])
    
    body = f'''<div class="hero text-center"><h1>🎬 Добро пожаловать в MovieHub</h1><p class="lead">Обзоры, рейтинги и чаты фанатов</p><form action="/" method="GET" class="mt-4"><input type="text" name="search" class="form-control form-control-lg" placeholder="🔍 Поиск фильмов..." value="{search}"></form></div>
    <h3 class="section-title">📂 Жанры</h3><div class="row mb-4">{gb}</div>
    <h3 class="section-title">{'🔍 Результаты поиска: "' + search + '"' if search else '🎥 Все фильмы'}</h3>
    <div class="row">{mc if movies else '<p class="text-center">😔 Ничего не найдено</p>'}</div>'''
    return base_page("Главная", body)

# ==================== Жанр ====================
@app.route('/genre/<genre>')
def genre_folder(genre):
    search = request.args.get('search', '').strip()
    movies = Movie.query.filter_by(genre=genre).order_by(Movie.created_at.desc()).all()
    if search:
        movies = [m for m in movies if search.lower() in m.title.lower()]
    
    mc = ''.join([f'<div class="col-md-4 mb-4"><div class="card movie-card h-100"><img src="{m.poster_url or "https://via.placeholder.com/300x450"}" class="card-img-top"><div class="card-body"><h5 class="card-title">{m.title}</h5><span class="badge bg-primary mb-2">{m.genre}</span><p class="card-text">{m.description[:100]}...</p><a href="/movie/{m.id}" class="btn btn-outline-primary btn-sm">Подробнее</a></div></div></div>' for m in movies])
    
    body = f'''<h2>📁 {genre}</h2><form action="/genre/{genre}" method="GET" class="my-4"><input type="text" name="search" class="form-control" placeholder="🔍 Поиск в жанре..." value="{search}"></form>
    <div class="row">{mc if movies else '<p class="text-center">Нет фильмов</p>'}</div><a href="/" class="btn btn-outline-primary mt-3">← Назад</a>'''
    return base_page(genre, body)

# ==================== Фильм ====================
@app.route('/movie/<int:movie_id>')
def movie_detail(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie: return "Фильм не найден", 404
    
    platforms = Platform.query.filter_by(movie_id=movie_id).all()
    comments = Comment.query.filter_by(movie_id=movie_id).order_by(Comment.created_at.desc()).all()
    avg = db.session.query(db.func.avg(Rating.score)).filter_by(movie_id=movie_id).scalar()
    count = Rating.query.filter_by(movie_id=movie_id).count()
    user_rate = Rating.query.filter_by(user_id=current_user.id, movie_id=movie_id).first() if current_user.is_authenticated else None
    
    rating_html = '<h4>⭐ Рейтинг</h4>'
    if avg:
        rating_html += f'<h2 style="color:#ffd700;">{avg:.1f} / 10</h2><p>{count} оценок</p>'
    else:
        rating_html += '<p>Нет оценок</p>'
    
    if current_user.is_authenticated:
        score = user_rate.score if user_rate else 0
        stars = ''.join([f'<span class="star" onclick="rate({i})">{"★" if i <= score else "☆"}</span>' for i in range(1, 11)])
        rating_html += f'<div class="mb-2">{stars}</div><p>{"Ваша оценка: " + str(score) if user_rate else "Поставьте оценку"}</p>'
    
    plat_html = ''.join([f'<div class="col-md-6 mb-2"><a href="{p.url}" target="_blank" class="btn btn-outline-success w-100">{p.name} - {"🆓 Бесплатно" if p.is_free else "💳 Платно"}</a></div>' for p in platforms])
    
    similar = Movie.query.filter(Movie.genre == movie.genre, Movie.id != movie.id).limit(4).all()
    sim_html = ''.join([f'<div class="col-md-3 mb-3"><div class="card"><img src="{s.poster_url or "https://via.placeholder.com/200x300"}" class="card-img-top"><div class="card-body"><h6 class="card-title">{s.title}</h6><a href="/movie/{s.id}" class="btn btn-sm btn-outline-primary">Смотреть</a></div></div></div>' for s in similar])
    
    comm_form = f'<form action="/add_comment/{movie.id}" method="POST" class="mb-4"><textarea name="content" class="form-control" rows="3" placeholder="Комментарий..." required></textarea><button class="btn btn-primary mt-2">Отправить</button></form>' if current_user.is_authenticated else '<p><a href="/login">Войдите</a> чтобы комментировать</p>'
    
    comm_html = ''.join([f'<div class="card mb-2"><div class="card-body"><strong>👤 {c.author.username}</strong><small class="float-end">{c.created_at.strftime("%d.%m.%Y %H:%M")}</small><p class="mt-2">{c.content}</p></div></div>' for c in comments])
    
    trailer = f'<div class="mb-4"><h4>🎬 Трейлер</h4><div class="ratio ratio-16x9"><iframe src="{movie.trailer_url}" allowfullscreen></iframe></div></div>' if movie.trailer_url else ''
    edit_button = f'<a href="/admin/edit_movie/{movie.id}" class="btn btn-warning btn-sm ms-2">✏️ Редактировать</a>' if (current_user.is_authenticated and current_user.is_admin) else ''
    
    body = f'''<div class="row"><div class="col-md-4"><img src="{movie.poster_url or "https://via.placeholder.com/400x600"}" class="img-fluid rounded shadow"></div>
    <div class="col-md-8"><h1 class="movie-title">{movie.title}{edit_button}</h1><span class="badge bg-primary mb-3">{movie.genre}</span><p class="lead">{movie.description}</p>
    {rating_html}{trailer}<h4>📺 Где смотреть:</h4><div class="row">{plat_html}</div><a href="/chat/{movie.id}" class="btn btn-primary mt-3">💬 Чат фанатов</a></div></div>
    <div class="mt-5"><h3 class="section-title">Похожие фильмы</h3><div class="row">{sim_html or '<p>Нет похожих</p>'}</div></div>
    <div class="mt-5"><h3 class="section-title">💬 Комментарии</h3>{comm_form}{comm_html or '<p>Нет комментариев</p>'}</div>'''
    
    scripts = f'''<script>function rate(score){{fetch('/rate_movie/{movie.id}',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{score:score}})}}).then(r=>r.json()).then(d=>{{if(d.success)location.reload();else alert(d.message)}})}}</script>'''
    return base_page(movie.title, body, scripts)

# ==================== Оценка ====================
@app.route('/rate_movie/<int:movie_id>', methods=['POST'])
@login_required
def rate_movie(movie_id):
    data = request.get_json()
    score = data.get('score', 0)
    if score < 1 or score > 10: return jsonify({'success': False})
    existing = Rating.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()
    if existing: existing.score = score
    else: db.session.add(Rating(user_id=current_user.id, movie_id=movie_id, score=score))
    db.session.commit()
    return jsonify({'success': True})

# ==================== Комментарий ====================
@app.route('/add_comment/<int:movie_id>', methods=['POST'])
@login_required
def add_comment(movie_id):
    content = request.form['content'].strip()
    if content:
        db.session.add(Comment(content=content, user_id=current_user.id, movie_id=movie_id))
        db.session.commit()
    return redirect(url_for('movie_detail', movie_id=movie_id))

# ==================== Вход/Регистрация ====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username'].strip()).first()
        if user and check_password_hash(user.password, request.form['password']):
            if user.is_banned: flash('Аккаунт заблокирован'); return redirect(url_for('login'))
            login_user(user); return redirect(url_for('index'))
        flash('Неверный логин или пароль')
    body = '<div class="row justify-content-center"><div class="col-md-6"><div class="card"><div class="card-body"><h2>Вход</h2><form method="POST"><div class="mb-3"><label>Логин</label><input type="text" name="username" class="form-control" required></div><div class="mb-3"><label>Пароль</label><input type="password" name="password" class="form-control" required></div><button class="btn btn-primary w-100">Войти</button></form><p class="mt-3 text-center"><a href="/register">Регистрация</a></p></div></div></div></div>'
    return base_page("Вход", body)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        if User.query.filter_by(username=username).first(): flash('Пользователь существует'); return redirect(url_for('register'))
        user = User(username=username, email=request.form['email'].strip(), password=generate_password_hash(request.form['password']))
        db.session.add(user); db.session.commit()
        login_user(user); return redirect(url_for('index'))
    body = '<div class="row justify-content-center"><div class="col-md-6"><div class="card"><div class="card-body"><h2>Регистрация</h2><form method="POST"><div class="mb-3"><label>Логин</label><input type="text" name="username" class="form-control" required></div><div class="mb-3"><label>Email</label><input type="email" name="email" class="form-control" required></div><div class="mb-3"><label>Пароль</label><input type="password" name="password" class="form-control" required></div><button class="btn btn-primary w-100">Зарегистрироваться</button></form><p class="mt-3 text-center"><a href="/login">Войти</a></p></div></div></div></div>'
    return base_page("Регистрация", body)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ==================== ЧАТ (ИСПРАВЛЕН!) ====================
@app.route('/chat/<int:movie_id>')
@login_required
def chat(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie: return "Фильм не найден", 404
    
    body = f'''<div class="card"><div class="card-header d-flex justify-content-between"><h4 class="mb-0">💬 Чат: <span class="movie-title">{movie.title}</span></h4><a href="/movie/{movie.id}" class="btn btn-light btn-sm">← Назад</a></div>
    <div class="card-body"><div id="messages" class="chat-box mb-3"></div><div class="input-group"><input type="text" id="msg-input" class="form-control" placeholder="Сообщение..."><button class="btn btn-primary" id="send-btn">Отправить</button></div></div></div>'''
    
    scripts = f'''<script>
    var socket = io();
    var room = "movie_{movie.id}";
    
    socket.emit("join", {{room: room}});
    
    socket.on("message", function(data) {{
        var messagesDiv = document.getElementById("messages");
        var msgElement = document.createElement("div");
        msgElement.className = "chat-msg";
        msgElement.textContent = data;
        messagesDiv.appendChild(msgElement);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }});
    
    document.getElementById("send-btn").onclick = function() {{
        var input = document.getElementById("msg-input");
        var msg = input.value.trim();
        if (msg) {{
            socket.emit("message", {{room: room, msg: msg}});
            input.value = "";
            input.focus();
        }}
    }};
    
    document.getElementById("msg-input").onkeypress = function(e) {{
        if (e.key === "Enter") {{
            document.getElementById("send-btn").click();
        }}
    }};
    </script>'''
    
    return base_page(f"Чат: {movie.title}", body, scripts)

@socketio.on('join')
def handle_join(data):
    join_room(data['room'])
    send(f'👤 {current_user.username} присоединился', room=data['room'])

@socketio.on('message')
def handle_message(data):
    send(f'{current_user.username}: {data["msg"]}', room=data['room'])

# ==================== Админ (УДАЛЕНИЕ КОММЕНТАРИЕВ ИСПРАВЛЕНО) ====================
@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin: return redirect(url_for('index'))
    
    users = User.query.all()
    movies = Movie.query.all()
    comments = Comment.query.all()
    
    ut = ''.join([f'<tr><td>{u.username}</td><td>{u.email}</td><td>{"🔴 Забанен" if u.is_banned else "🟢 Активен"}</td><td><a href="/admin/ban/{u.id}" class="btn btn-sm btn-warning">{"Разбанить" if u.is_banned else "Забанить"}</a></td></tr>' for u in users])
    cd = ''.join([f'<div class="card mb-2"><div class="card-body"><strong>{c.author.username}</strong> → <span class="movie-title">{c.movie.title}</span><p class="mt-2">{c.content}</p><a href="/admin/delete_comment/{c.id}" class="btn btn-sm btn-danger" onclick="return confirm(\'Удалить комментарий?\')">🗑️ Удалить</a></div></div>' for c in comments])
    mt = ''.join([f'<tr><td><span class="movie-title">{m.title}</span></td><td><span class="badge bg-primary">{m.genre}</span></td><td><a href="/admin/edit_movie/{m.id}" class="btn btn-sm btn-primary">✏️</a> <a href="/admin/delete_movie/{m.id}" class="btn btn-sm btn-danger" onclick="return confirm(\'Удалить фильм?\')">🗑️</a></td></tr>' for m in movies])
    
    body = f'''<h1>⚙️ Админ-панель</h1><a href="/admin/add_movie" class="btn btn-success mb-3">➕ Добавить фильм</a>
    <div class="row mt-4"><div class="col-md-6"><h3 class="section-title">👥 Пользователи</h3><table class="table"><thead><tr><th>Имя</th><th>Email</th><th>Статус</th><th></th></tr></thead><tbody>{ut}</tbody></table></div>
    <div class="col-md-6"><h3 class="section-title">💬 Комментарии</h3>{cd or '<p>Нет комментариев</p>'}</div></div>
    <div class="mt-4"><h3 class="section-title">🎬 Фильмы</h3><table class="table"><thead><tr><th>Название</th><th>Жанр</th><th>Действия</th></tr></thead><tbody>{mt}</tbody></table></div>'''
    return base_page("Админ", body)

@app.route('/admin/ban/<int:user_id>')
@login_required
def ban_user(user_id):
    if current_user.is_admin:
        u = db.session.get(User, user_id)
        if u and not u.is_admin:
            u.is_banned = not u.is_banned
            db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/delete_comment/<int:comment_id>')
@login_required
def delete_comment(comment_id):
    if current_user.is_admin:
        c = db.session.get(Comment, comment_id)
        if c:
            db.session.delete(c)
            db.session.commit()
            flash('Комментарий удалён')
    return redirect(url_for('admin'))

@app.route('/admin/delete_movie/<int:movie_id>')
@login_required
def delete_movie(movie_id):
    if current_user.is_admin:
        m = db.session.get(Movie, movie_id)
        if m:
            db.session.delete(m)
            db.session.commit()
            flash('Фильм удалён')
    return redirect(url_for('admin'))

@app.route('/admin/add_movie', methods=['GET', 'POST'])
@login_required
def add_movie():
    if not current_user.is_admin: return redirect(url_for('index'))
    if request.method == 'POST':
        m = Movie(title=request.form['title'], description=request.form['description'], genre=request.form['genre'], poster_url=request.form.get('poster_url',''), trailer_url=request.form.get('trailer_url',''))
        db.session.add(m); db.session.flush()
        names = request.form.getlist('pname'); urls = request.form.getlist('purl'); free = request.form.getlist('pfree')
        for i in range(len(names)):
            if names[i] and urls[i]: db.session.add(Platform(name=names[i], url=urls[i], is_free=str(i) in free, movie_id=m.id))
        db.session.commit(); flash('Фильм добавлен!'); return redirect(url_for('admin'))
    
    body = '''<div class="card"><div class="card-body"><h1>➕ Добавить фильм</h1><form method="POST">
    <div class="mb-3"><label>Название</label><input type="text" name="title" class="form-control" required></div>
    <div class="mb-3"><label>Описание</label><textarea name="description" class="form-control" rows="5" required></textarea></div>
    <div class="mb-3"><label>Жанр</label><input type="text" name="genre" class="form-control" required></div>
    <div class="mb-3"><label>URL постера</label><input type="text" name="poster_url" class="form-control"></div>
    <div class="mb-3"><label>URL трейлера</label><input type="text" name="trailer_url" class="form-control"></div>
    <h4>Платформы</h4><div id="plats"><div class="mb-2"><input type="text" name="pname" class="form-control mb-1" placeholder="Название"><input type="text" name="purl" class="form-control mb-1" placeholder="Ссылка"><label><input type="checkbox" name="pfree" value="0"> Бесплатно</label></div></div>
    <button type="button" class="btn btn-secondary mb-3" onclick="addP()">+ Платформа</button><br>
    <button class="btn btn-success">✅ Добавить</button></form></div></div>
    <script>let c=1;function addP(){{document.getElementById('plats').insertAdjacentHTML('beforeend','<div class="mb-2"><input type="text" name="pname" class="form-control mb-1" placeholder="Название"><input type="text" name="purl" class="form-control mb-1" placeholder="Ссылка"><label><input type="checkbox" name="pfree" value="'+c+'"> Бесплатно</label></div>');c++}}</script>'''
    return base_page("Добавить фильм", body)

# ==================== Редактирование ====================
@app.route('/admin/edit_movie/<int:movie_id>', methods=['GET', 'POST'])
@login_required
def edit_movie(movie_id):
    if not current_user.is_admin: return redirect(url_for('index'))
    movie = db.session.get(Movie, movie_id)
    if not movie: return "Фильм не найден", 404
    
    if request.method == 'POST':
        movie.title = request.form['title']; movie.description = request.form['description']
        movie.genre = request.form['genre']; movie.poster_url = request.form.get('poster_url','')
        movie.trailer_url = request.form.get('trailer_url','')
        Platform.query.filter_by(movie_id=movie.id).delete()
        names = request.form.getlist('pname'); urls = request.form.getlist('purl'); free = request.form.getlist('pfree')
        for i in range(len(names)):
            if names[i] and urls[i]: db.session.add(Platform(name=names[i], url=urls[i], is_free=str(i) in free, movie_id=movie.id))
        db.session.commit(); flash('Обновлено!'); return redirect(url_for('admin'))
    
    platforms = Platform.query.filter_by(movie_id=movie.id).all()
    ph = ''.join([f'<div class="mb-2"><input type="text" name="pname" class="form-control mb-1" value="{p.name}"><input type="text" name="purl" class="form-control mb-1" value="{p.url}"><label><input type="checkbox" name="pfree" value="{i}" {"checked" if p.is_free else ""}> Бесплатно</label></div>' for i, p in enumerate(platforms)])
    if not ph: ph = '<div class="mb-2"><input type="text" name="pname" class="form-control mb-1" placeholder="Название"><input type="text" name="purl" class="form-control mb-1" placeholder="Ссылка"><label><input type="checkbox" name="pfree" value="0"> Бесплатно</label></div>'
    
    pp = f'<img src="{movie.poster_url}" style="max-width:200px;margin-top:10px" class="rounded"><br>' if movie.poster_url else ''
    
    body = f'''<div class="card"><div class="card-body"><h1>✏️ Редактировать</h1><form method="POST">
    <div class="mb-3"><label>Название</label><input type="text" name="title" class="form-control" value="{movie.title}" required></div>
    <div class="mb-3"><label>Описание</label><textarea name="description" class="form-control" rows="5" required>{movie.description}</textarea></div>
    <div class="mb-3"><label>Жанр</label><input type="text" name="genre" class="form-control" value="{movie.genre}" required></div>
    <div class="mb-3"><label>URL постера</label><input type="text" name="poster_url" class="form-control" value="{movie.poster_url or ''}">{pp}</div>
    <div class="mb-3"><label>URL трейлера</label><input type="text" name="trailer_url" class="form-control" value="{movie.trailer_url or ''}"></div>
    <h4>Платформы</h4><div id="plats">{ph}</div>
    <button type="button" class="btn btn-secondary mb-3" onclick="addP()">+ Платформа</button><br>
    <button class="btn btn-primary">💾 Сохранить</button></form></div></div>
    <script>let pc={len(platforms)};function addP(){{document.getElementById('plats').insertAdjacentHTML('beforeend','<div class="mb-2"><input type="text" name="pname" class="form-control mb-1" placeholder="Название"><input type="text" name="purl" class="form-control mb-1" placeholder="Ссылка"><label><input type="checkbox" name="pfree" value="'+pc+'"> Бесплатно</label></div>');pc++}}</script>'''
    return base_page(f"Редактировать: {movie.title}", body)

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            db.session.add(User(username='admin', email='admin@moviehub.com', password=generate_password_hash('123456'), is_admin=True))
            db.session.commit()
            print("✅ Админ создан: admin / 123456")
        
        if Movie.query.count() == 0:
            for t,d,g,p,tr in [
                ('Начало','Вор крадет секреты из глубин подсознания.','Фантастика',
                 'https://avatars.mds.yandex.net/get-kinopoisk-image/1629390/8ab9a118-9a80-4db2-bbc7-2c0a30eb8f40/600x900',
                 'https://www.youtube.com/embed/8hP9D6kZseM'),
                ('Матрица','Хакер узнает правду о реальности.','Фантастика',
                 'https://avatars.mds.yandex.net/get-kinopoisk-image/1773646/1f7c0b6c-6e9e-4f3e-8c0e-9c3e9e3e9e3e/600x900',
                 'https://www.youtube.com/embed/m8e-FF8MsqU'),
                ('Джон Уик','Киллер мстит за собаку.','Боевик',
                 'https://avatars.mds.yandex.net/get-kinopoisk-image/1946459/8f8f8f8f-8f8f-8f8f-8f8f-8f8f8f8f8f8f/600x900',
                 'https://www.youtube.com/embed/C0BMx-qxsP4'),
            ]:
                m = Movie(title=t, description=d, genre=g, poster_url=p, trailer_url=tr)
                db.session.add(m)
                db.session.flush()
                db.session.add(Platform(name='Кинопоиск', url='https://www.kinopoisk.ru/', is_free=False, movie_id=m.id))
            db.session.commit()
            print("🎬 3 фильма добавлены")
    
    # Для продакшена
    import os
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    print(f"\n🚀 Запуск на порту {port}")
    socketio.run(app, debug=debug_mode, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)