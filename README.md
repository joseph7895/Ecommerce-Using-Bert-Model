# 🛒 Ecommerce Customer Feedback & Recommendation System using BERT

## 📌 Project Overview

This project is an AI-powered e-commerce web application that analyzes customer feedback using **BERT-based sentiment analysis** and provides intelligent product recommendations. It helps users make better purchasing decisions by understanding product reviews and ratings.

---

## 🚀 Features

* 🛍️ Product listing with search and category filter
* 📊 Sentiment analysis using **DistilBERT/BERT model**
* ⭐ Customer review system with ratings
* 🧠 AI-based product recommendation system
* 🛒 Add to cart and order functionality
* 🔐 User authentication (Login/Signup)
* 📦 Order history tracking

---

## 🧠 Technologies Used

### 💻 Frontend
* HTML
* CSS
* Bootstrap

### ⚙️ Backend
* Python
* Flask

### 🗄️ Database
* SQLite

### 🤖 AI / ML
* Hugging Face Transformers
* BERT / DistilBERT Model

---

## 📂 Project Structure

```
Project/
│
├── app.py
├── Dataset/
│   └── amazon.csv
│
├── frontend/
│   ├── templates/
│   │   ├── index.html
│   │   ├── product.html
│   │   ├── login.html
│   │   ├── signup.html
│   │   ├── cart.html
│   │   ├── orders.html
│   │   └── buy.html
│   │
│   └── static/
│       ├── css/
│       └── images/
│
└── database.db
```

## 📊 How It Works

1. User browses products
2. Adds review and rating
3. BERT model analyzes sentiment (Positive/Negative)
4. System updates product rating
5. Recommendation engine suggests similar/high-rated products

---

## 📈 Model Used

* **DistilBERT** for sentiment analysis
* Pre-trained model from Hugging Face:

```
distilbert-base-uncased-finetuned-sst-2-english
```
## 🧪 Future Enhancements

* 🔥 Personalized recommendations using user behavior
* 📊 Advanced filtering and sorting
* 🧾 Payment gateway integration
* 📱 Mobile responsiveness improvements
* 🤖 Fine-tuned BERT model for better accuracy
