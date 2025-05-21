# MingMigle Backend

This is the **FastAPI** backend for the MingMigle project. It provides a secure RESTful API to support features like user authentication, blog creation, likes, comments, and more.

---

## 🚀 Getting Started

Follow these instructions to set up and run the backend locally.

### 📦 Prerequisites

- Python 3.10 or higher
- pip
- Virtual environment tool (e.g., `venv`, `virtualenv`, or `poetry`)
- PostgreSQL or SQLite (as DB)

---

## 🔧 Installation

1. **Clone the repository**

```bash
git clone https://github.com/Chinthurajendran/Mindmingle_backend.git
cd Mindmingle_backend
````

2. **Create and activate a virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install the dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

Create a `.env` file in the root directory:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/mingmigle
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
CORS_ORIGINS=http://localhost:3000
```

> Make sure your PostgreSQL server is running and the database exists.

---

## 🔄 Running the Server

```bash
uvicorn main:app --reload
```

Server will start at [http://localhost:8000](http://localhost:8000)

---

## 🧩 Features

* 🔐 JWT-based authentication (Signup/Login)
* 📝 Blog CRUD
* 👍 Like/Dislike system
* 💬 Comment and reply system
* 👤 User profile endpoints
* 📄 Swagger UI for API testing at `/docs`

---

## 🛠️ Tech Stack

* **FastAPI**
* **SQLAlchemy**
* **PostgreSQL**
* **Pydantic**
* **Uvicorn**
* **Python-Jose** (for JWT)
* **Passlib** (for password hashing)
* **CORS Middleware**

---

## 📤 Deployment

You can deploy the backend using:

* **Docker + AWS ECS**
* **Gunicorn + Nginx + EC2**
* **Render / Railway / Fly.io**

Make sure to switch `DEBUG=False` and use environment variables in production.

---

## 🧪 API Documentation

* Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
* ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🤝 Contributing

Feel free to fork this repo and submit a pull request for improvements or bug fixes.

---

## 📄 License

This project is licensed under the MIT License.

---

## 📬 Contact

**Chinthu Rajendran**
🔗 [GitHub](https://github.com/Chinthurajendran)

```

---

Would you like me to generate and send this as a downloadable `README.md` file for your backend repo?
```
