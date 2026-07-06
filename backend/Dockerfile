FROM python:3.12-slim

WORKDIR /app

# System deps for psycopg2, plus a Unicode font (DejaVu) so the PDF report
# renders the rupee sign (₹) and other non-Latin glyphs correctly.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
