# BizSkill AI 🎯

> AI-powered video learning platform that transforms long-form business content into searchable, bite-sized knowledge segments.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Next.js](https://img.shields.io/badge/next.js-14-black.svg)

## 🌟 Features

- **AI-Powered Segmentation**: Automatically split long videos into focused, topic-specific clips (30-90 seconds)
- **Smart Search**: Semantic search powered by OpenAI embeddings and hybrid ranking
- **Key Insights Extraction**: AI-generated summaries and key takeaways for each segment
- **Category Organization**: 8 business categories (Leadership, Marketing, Startups, Finance, etc.)
- **10 Premium Channels**: Curated content from TED, Harvard Business Review, Y Combinator, and more
- **YouTube Compliant**: Uses YouTube Iframe API for playback - no content downloading

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Next.js       │────▶│   FastAPI       │────▶│   PostgreSQL    │
│   Frontend      │     │   Backend       │     │   + Qdrant      │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
           ┌─────────────────┐       ┌─────────────────┐
           │   Celery        │       │   Redis         │
           │   Workers       │       │   Cache/Broker  │
           └────────┬────────┘       └─────────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐
   │ Whisper │ │  GPT-4  │ │Embedding│
   │   API   │ │   API   │ │   API   │
   └─────────┘ └─────────┘ └─────────┘
```

## 📋 Prerequisites

- **Docker** & **Docker Compose** (v2.0+)
- **OpenAI API Key** (for Whisper, GPT-4, and embeddings)
- **YouTube Data API Key** (for fetching video metadata)
- **8GB+ RAM** recommended for running all services

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd BizSkill

# Copy environment template
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` with your API keys:

```env
# Required API Keys
OPENAI_API_KEY=sk-your-openai-key
YOUTUBE_API_KEY=your-youtube-api-key

# Optional: Generate a secure secret key
SECRET_KEY=$(openssl rand -hex 32)
```

### 3. Start Services

```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f
```

### 4. Initialize Database & Seed Data

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Seed with 10 famous business channels
docker-compose exec backend python /app/scripts/seed.py
```

### 5. Access the Application

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | Main application |
| **API Docs** | http://localhost:8000/docs | Swagger API documentation |
| **Flower** | http://localhost:5555 | Celery task monitoring |
| **Qdrant** | http://localhost:6333/dashboard | Vector database dashboard |

## 📁 Project Structure

```
BizSkill/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST API endpoints
│   │   ├── core/            # Config, security, Celery
│   │   ├── db/              # Database models
│   │   ├── services/        # AI services (YouTube, LLM, etc.)
│   │   ├── workers/         # Celery task definitions
│   │   └── main.py          # FastAPI application
│   ├── alembic/             # Database migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js pages
│   │   ├── components/      # React components
│   │   ├── lib/             # API client
│   │   └── types/           # TypeScript types
│   ├── Dockerfile
│   └── package.json
├── scripts/
│   └── seed.py              # Database seeding script
├── docker-compose.yml
├── .env.example
└── README.md
```

## 🎬 Pre-configured Channels

| Channel | Description |
|---------|-------------|
| TED | Ideas worth spreading |
| Harvard Business Review | Management & strategy |
| Y Combinator | Startup wisdom |
| GaryVee | Entrepreneurship & marketing |
| Simon Sinek | Leadership & inspiration |
| The Futur | Creative business |
| Valuetainment | Business insights |
| Ali Abdaal | Productivity & growth |
| MasterClass | Learn from the best |
| Stanford GSB | Business education |

## 🔧 Development

### Running Locally (without Docker)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
# Backend tests
docker-compose exec backend pytest

# Frontend tests
docker-compose exec frontend npm test
```

## 📖 API Endpoints

### Segments
- `GET /api/v1/segments/` - List segments with pagination
- `GET /api/v1/segments/{id}` - Get segment details
- `GET /api/v1/segments/{id}/related` - Get related segments
- `GET /api/v1/segments/feed` - Get personalized feed

### Search
- `GET /api/v1/search/?q={query}` - Semantic search
- `GET /api/v1/search/suggestions?q={prefix}` - Search suggestions

### Categories
- `GET /api/v1/categories/` - List all categories
- `GET /api/v1/categories/{slug}/segments` - Segments by category

### Channels
- `GET /api/v1/channels/` - List all channels
- `POST /api/v1/channels/{id}/sync` - Trigger video sync

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `YOUTUBE_API_KEY` | YouTube Data API key | Required |
| `SECRET_KEY` | JWT secret key | Required |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://...` |
| `REDIS_URL` | Redis connection | `redis://redis:6379/0` |
| `QDRANT_URL` | Qdrant vector DB | `http://qdrant:6333` |

### Processing Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `MIN_SEGMENT_DURATION` | Minimum segment length | `30` seconds |
| `MAX_SEGMENT_DURATION` | Maximum segment length | `90` seconds |
| `LLM_MODEL` | OpenAI model for segmentation | `gpt-4o` |
| `EMBEDDING_MODEL` | OpenAI embedding model | `text-embedding-3-small` |

## 🔒 Security

- JWT-based authentication
- Password hashing with bcrypt
- CORS protection
- Rate limiting on API endpoints
- Secure environment variable handling

## 📊 Monitoring

- **Flower** (http://localhost:5555): Monitor Celery tasks in real-time
- **Health Check**: `GET /health` returns service status
- **Metrics**: Processing stats at `GET /api/v1/admin/stats`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for Whisper, GPT-4, and embedding APIs
- YouTube for the Iframe API and Data API
- All the amazing business educators whose content powers this platform

---

**Built with ❤️ for lifelong learners**
