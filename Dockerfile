# Base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy backend and frontend
COPY backend/ backend/
COPY frontend/ frontend/

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r backend/requirements.txt
RUN pip install --no-cache-dir -r frontend/requirements.txt

# Expose ports
EXPOSE 8000 8501

# Start both backend and frontend
CMD ["sh", "-c", "uvicorn backend.backend:app --host 0.0.0.0 --port 8000 & streamlit run frontend/frontend.py --server.port 8501 --server.headless true"]