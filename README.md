#  BuyTouch -- Modern Flask Marketplace Platform

A full-stack marketplace built with **Flask**, featuring Google OAuth
login, admin panel, product uploads, categories, favorites, cart,
comments, and secure user management.

------------------------------------------------------------------------

## 🛡️ Badges

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.x-black.svg)
![SQLAlchemy](https://img.shields.io/badge/Database-SQLAlchemy-green.svg)
![OAuth2](https://img.shields.io/badge/Auth-Google%20OAuth-red.svg)
![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

------------------------------------------------------------------------

## 📸 Screenshots



  -----------------------------------------------------------------------------------------
  **Home Page**                                 
  ----------------------------------------- -----------------------------------------------
  ![Home](https://i.postimg.cc/htrSqp70/Screenshot-2025-11-24-154332.png) 



  -------------------------------------------------------------------------------------------
  **Admin Dashboard**                            
  ------------------------------------------- -----------------------------------------------
  ![Admin](https://i.postimg.cc/TPFB8DQH/Screenshot-2025-11-24-154824.png)

  -------------------------------------------------------------------------------------------

------------------------------------------------------------------------

## 🚀 Features

### 👤 User System

-   Google OAuth2 login\
-   Auto account creation\
-   Profile editing\
-   Profile picture upload\
-   Unique username enforcement

### 🛒 Marketplace

-   Create, edit, delete products\
-   Multiple image upload support\
-   Categories + search system\
-   Favorites system\
-   Cart system\
-   Checkout grouped by sellers\
-   Comment system

### 🛠️ Admin Panel

-   Approve or reject products\
-   Modify product details\
-   Delete any product\
-   View and delete users\
-   View pending/accepted/rejected items

### 🗄️ Backend Architecture

-   Flask + SQLAlchemy\
-   Secure image upload\
-   MAX_CONTENT_LENGTH upload protection\
-   Custom errors: 404, 500, 403\
-   Automatic cart cleanup

------------------------------------------------------------------------

## 🧱 Tech Stack

  Layer      Technology
  ---------- -------------------------
  Backend    Flask, Jinja2
  Database   SQLite + SQLAlchemy
  Auth       Google OAuth2 (Authlib)
  Frontend   HTML, CSS, JS
  Storage    Local image uploads

------------------------------------------------------------------------

## 📁 Project Structure

    ├── app.py
    ├── config.py
    ├── extensions.py
    ├── models.py
    │
    ├── /instance/
    │   └── site.db
    │
    ├── /static/
    │   ├── css/
    │   ├── js/
    │   ├── img/
    │   └── uploads/
    │
    └── /templates/
        ├── index.html
        ├── login.html
        ├── product_create.html
        ├── product_detail.html
        ├── admin_panel.html
        ├── user_products.html
        ├── user_profile_settings.html
        ├── cart.html
        ├── favorites.html
        ├── checkout.html
        ├── 404.html
        ├── 500.html
        └── 403.html

------------------------------------------------------------------------

## 🔧 Installation

### 1. Clone the Repository

    git clone https://github.com/RXDarkee/BuyTouch-Flask-Ecommerce.git
    cd BuyTouch-Flask-Ecommerce

### 2. Install Dependencies

    pip install -r requirements.txt


### 3. Run the App

    python app.py





------------------------------------------------------------------------

## 📜 License

MIT License.

------------------------------------------------------------------------

## ❤️ Credits

Developed by **Rasan Fernando**.
