# Educational Knowledge Platform

## Overview

Educational Knowledge Platform is a personal Data Engineering project that collects educational content from YouTube and transforms it into a semantic-search-ready knowledge base.

The project follows a Medallion Architecture (Bronze, Silver, Gold) and includes transcript processing, chunk generation, embedding creation, and vector database integration.

## Objectives

* Collect educational video metadata from YouTube
* Extract and process transcripts
* Build Bronze, Silver, and Gold data layers
* Generate embeddings for semantic search
* Store vectors in a vector database

## Architecture

YouTube API
→ Bronze Layer
→ Silver Layer
→ Gold Layer
→ Embedding Pipeline
→ Vector Database

Metadata is stored in PostgreSQL.

## Current Progress

### Completed

* Project architecture design
* ERD design
* PostgreSQL database setup
* Project folder structure
* Documentation setup

### In Progress

* Video metadata ingestion pipeline

## Tech Stack

* Python
* PostgreSQL
* SQLAlchemy
* Pandas
* YouTube Data API
* ChromaDB / Qdrant

## Project Structure

```text
data/
    bronze/
    silver/
    gold/

src/
    ingestion/
    processing/
    embedding/
    database/
```

## Roadmap

Week 1

* Video metadata ingestion

Week 2

* Transcript extraction

Week 3

* Data processing and chunking

Week 4

* Embeddings and vector database integration

```
```
