# Now we import 'db' from extensions.py, avoiding the circular dependency.
from extensions import db
from datetime import datetime
from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True) # Full name from Google
    username = db.Column(db.String(80), unique=True, nullable=False) # User-set display name
    profile_pic = db.Column(db.String(255), nullable=True)
    mobile_number = db.Column(db.String(20), nullable=True) # Changed to nullable=True for initial Google login
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    products = db.relationship('Product', backref='seller', lazy=True, cascade="all, delete-orphan")
    # Added relationships for Cart, Favorite, and Comment
    cart_items = db.relationship('Cart', backref='user', lazy=True, cascade="all, delete-orphan")
    favorites = db.relationship('Favorite', backref='user', lazy=True, cascade="all, delete-orphan")
    comments = db.relationship('Comment', backref='user', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<User {self.username}>'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False) # 'pending', 'accepted', 'rejected'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    images = db.relationship('ProductImage', backref='product', lazy=True, cascade="all, delete-orphan")
    # Added relationships for Cart, Favorite, and Comment
    cart_items = db.relationship('Cart', backref='product', lazy=True, cascade="all, delete-orphan") # Renamed backref
    favorited_by = db.relationship('Favorite', backref='product', lazy=True, cascade="all, delete-orphan") # Renamed backref
    comments = db.relationship('Comment', backref='product', lazy=True, cascade="all, delete-orphan")


    def __repr__(self):
        return f'<Product {self.name}>'

class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    image_url = db.Column(db.String(255), nullable=False) # Path relative to static folder

    def __repr__(self):
        return f'<ProductImage {self.image_url}>'
    
class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships for explicit access (backref already set in User and Product)
    # user = db.relationship('User', backref='cart_items_explicit') # No need, 'user' is already a backref name in User model
    # product = db.relationship('Product', backref='cart_items_explicit_prod') # No need, 'product' is already a backref name in Product model


class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships for explicit access (backref already set in User and Product)
    # user = db.relationship('User', backref='favorites_explicit')
    # product = db.relationship('Product', backref='favorited_by_explicit_prod')


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # user and product relationships are implicitly created via backref in User and Product models


# Admin is managed directly within User model using is_admin field.
# The 'Admin' class from your initial prompt is implicitly handled by User.is_admin.
# If you actually wanted a separate Admin table, you'd need to re-architect.
# For now, this is the most practical integration with Flask-Login.
# REMOVED PLACEHOLDER 'Admin' class