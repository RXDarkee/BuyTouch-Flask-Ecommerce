import os
import uuid
from authlib.integrations.flask_client import OAuth

from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename

from flask import (
    Flask, render_template, redirect, url_for, flash, request, abort, 
    session, jsonify
)
from flask_login import (
    LoginManager, current_user, login_user, logout_user, 
    login_required, UserMixin, AnonymousUserMixin 
)
from flask_moment import Moment

# Import configurations and extensions
from config import SECRET_KEY, DATABASE_URL, UPLOAD_FOLDER, ADMIN_USERNAME, ADMIN_PASSWORD, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
from extensions import db
from models import User, Product, ProductImage, Cart, Favorite, Comment

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# <-- Add MAX_CONTENT_LENGTH here
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB



# Initialize extensions
db.init_app(app)
moment = Moment(app)

# Initialize OAuth
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={'scope': 'openid email profile'},
    id_token_params={'leeway': 60}  # 60 seconds leeway
)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Allowed image extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Helper functions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_file(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        return f"uploads/{unique_filename}" 
    return None

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You need admin privileges to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def get_categories():
    # Force inclusion of all original predefined categories to avoid "removal" perception,
    # and then add any other categories from accepted products.
    predefined_categories = [
        'Apple', 'Android', 'Laptops', 'Tablets', 'Accessories', 
        'Vehicles: Cars & Motorbikes', 'Bikes', 'Computers'
    ]
    
    dynamic_categories_query = db.session.query(Product.category).distinct()\
                                 .filter(Product.category != None, Product.status == 'accepted')\
                                 .all()
    dynamic_categories = [cat[0] for cat in dynamic_categories_query if cat[0]]

    # Combine both lists and ensure uniqueness while prioritizing the predefined order
    all_unique_categories = list(dict.fromkeys(predefined_categories + dynamic_categories))
    
    return sorted(all_unique_categories)


# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    search_query = request.args.get('q', '')
    category_filter = request.args.get('category', '')
    
    # Base query for accepted products
    query = Product.query.filter(Product.status == 'accepted')
    
    # Apply filters based on search query
    if search_query:
        query = query.filter(
            db.or_(
                Product.name.ilike(f'%{search_query}%'),
                Product.brand.ilike(f'%{search_query}%'),
                Product.description.ilike(f'%{search_query}%'),
            )
        )
    
    # Apply category filter if one is selected (and not an empty string for "All Categories")
    if category_filter:
        query = query.filter(Product.category == category_filter)
    
    products = query.order_by(Product.created_at.desc()).all()
    
    # Get all categories for the filter dropdown
    categories = get_categories()
    
    return render_template('index.html', 
                         products=products, 
                         categories=categories,
                         search_query=search_query,
                         current_category=category_filter)

@app.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            admin_user = User.query.filter_by(email='admin@buytouch.com').first()
            if not admin_user:
                admin_user = User(
                    google_id='admin',
                    email='admin@buytouch.com',
                    name='Admin User',
                    username=ADMIN_USERNAME,
                    profile_pic=url_for('static', filename='img/admin_avatar.png'),
                    mobile_number='000-000-0000',
                    is_admin=True
                )
                db.session.add(admin_user)
                db.session.commit()
            
            login_user(admin_user)
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials.', 'danger')
    
    return render_template('admin_login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Only show accepted products to non-admin users
    # Admins can see all statuses when directly accessing product pages.
    if not current_user.is_authenticated or not current_user.is_admin:
        if product.status != 'accepted':
            # Redirect guest or non-admin to 404 if product not accepted
            abort(404)
    
    seller = User.query.get(product.seller_id)
    
    return render_template('product_detail.html', 
                         product=product, 
                         images=product.images,
                         seller=seller)

@app.route('/product/create', methods=['GET', 'POST'])
@login_required
def create_product():
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        brand = request.form.get('brand')
        description = request.form.get('description')
        price_str = request.form.get('price')
        
        try:
            price = float(price_str)
            if price < 0:
                flash('Invalid price. Price must be a positive number.', 'danger')
                return render_template('product_create.html', categories=get_categories())
        except ValueError:
            flash('Invalid price format. Price must be a number.', 'danger')
            return render_template('product_create.html', categories=get_categories())
        
        product = Product(
            name=name,
            category=category,
            brand=brand,
            description=description,
            price=price,
            seller_id=current_user.id,
            status='pending' # Products need admin approval
        )
        
        db.session.add(product)
        db.session.flush() # Get the product ID without committing
        
        # Handle image uploads
        images = request.files.getlist('images')
        image_count = 0
        
        for image in images:
            if image.filename == '': # Skip empty file inputs
                continue
            image_path = save_file(image)
            if image_path:
                product_image = ProductImage(
                    product_id=product.id,
                    image_url=image_path
                )
                db.session.add(product_image)
                image_count += 1
        
        # Check if we have the required number of images
        if image_count < 2:
            db.session.rollback() # Rollback product and any images saved for it
            flash('You need to upload at least 2 images.', 'danger')
            return render_template('product_create.html', categories=get_categories())
        
        db.session.commit()
        flash('Product created successfully and submitted for approval!', 'success')
        return redirect(url_for('user_products'))
    
    return render_template('product_create.html', categories=get_categories())

@app.route('/product/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Check if user owns the product or is admin
    if product.seller_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.category = request.form.get('category')
        product.brand = request.form.get('brand')
        product.description = request.form.get('description')
        price_str = request.form.get('price')

        # Validate price input
        try:
            product.price = float(price_str)
            if product.price < 0:
                flash('Invalid price. Price must be a positive number.', 'danger')
                db.session.refresh(product) # Re-fetch fresh state for rendering
                return render_template('product_create.html', 
                                   product=product, 
                                   images=product.images,
                                   categories=get_categories(),
                                   is_admin_edit=current_user.is_admin,
                                   statuses=['pending', 'accepted', 'rejected'])
        except ValueError:
            flash('Invalid price format. Price must be a number.', 'danger')
            db.session.refresh(product) # Re-fetch fresh state for rendering
            return render_template('product_create.html', 
                                   product=product, 
                                   images=product.images,
                                   categories=get_categories(),
                                   is_admin_edit=current_user.is_admin,
                                   statuses=['pending', 'accepted', 'rejected'])


        # Handle image deletion for existing images
        # Ensure that 'current_image_ids' is always present in the form if images exist.
        # Filter out empty strings which can come from hidden inputs if JS clears them on removal.
        current_image_ids_form = request.form.getlist('current_image_ids')
        images_to_keep_ids = [int(img_id) for img_id in current_image_ids_form if img_id.isdigit()]
        
        initial_images_count = len([img for img in product.images if img.id in images_to_keep_ids])

        images_deleted_count = 0
        # Iterate over a *copy* of the relationship to avoid collection modification issues during iteration
        for image in list(product.images):
            if image.id not in images_to_keep_ids:
                try:
                    full_image_path = os.path.join(app.static_folder, image.image_url)
                    if os.path.exists(full_image_path):
                        os.remove(full_image_path)
                    db.session.delete(image)
                    images_deleted_count += 1
                except Exception as e:
                    print(f"Error deleting image file {image.image_url}: {e}")
                
        # Handle new image uploads
        new_images = request.files.getlist('images')
        new_image_count = 0
        for image in new_images:
            if image.filename == '': # Skip empty file inputs
                continue
            image_path = save_file(image)
            if image_path:
                product_image = ProductImage(
                    product_id=product.id,
                    image_url=image_path
                )
                db.session.add(product_image)
                new_image_count += 1
        
        # Calculate final image count
        total_images_after_edit = initial_images_count + new_image_count

        if total_images_after_edit < 2:
            db.session.rollback() # Rollback all changes for this edit attempt
            flash('After editing, you still need to have at least 2 images.', 'danger')
            # Refresh product and images AFTER potential rollback to get the correct state
            db.session.refresh(product) 
            return render_template('product_create.html', 
                                product=product, 
                                images=product.images, # Reread product.images which is fresh now
                                categories=get_categories(),
                                is_admin_edit=current_user.is_admin,
                                statuses=['pending', 'accepted', 'rejected'])


        # If admin is editing, allow status change
        if current_user.is_admin and 'status' in request.form:
            product.status = request.form.get('status')
        
        product.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash('Product updated successfully!', 'success')
        return redirect(url_for('product_detail', product_id=product.id))
    
    return render_template('product_create.html', 
                         product=product, 
                         images=product.images,
                         categories=get_categories(),
                         is_admin_edit=current_user.is_admin,
                         statuses=['pending', 'accepted', 'rejected'])

@app.route('/product/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Check if user owns the product or is admin
    if product.seller_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    # Delete associated images (both from db and filesystem)
    # Iterate over a copy for safe deletion if using delete-orphan
    for image in list(product.images): 
        try:
            full_image_path = os.path.join(app.static_folder, image.image_url)
            if os.path.exists(full_image_path):
                os.remove(full_image_path)
            db.session.delete(image)
        except Exception as e:
            print(f"Error deleting image file {image.image_url}: {e}")
    
    # Explicitly delete related entities (Cart, Favorite, Comment) if not fully handled by cascade options
    Cart.query.filter_by(product_id=product_id).delete()
    Favorite.query.filter_by(product_id=product_id).delete()
    Comment.query.filter_by(product_id=product_id).delete()

    db.session.delete(product)
    db.session.commit()
    
    flash('Product deleted successfully.', 'success')
    
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('user_products'))

@app.route('/my-products')
@login_required
def user_products():
    products = Product.query.filter_by(seller_id=current_user.id)\
                           .order_by(Product.created_at.desc()).all()
    return render_template('user_products.html', products=products)

@app.route('/profile/settings', methods=['GET', 'POST'])
@login_required
def user_profile_settings():
    if request.method == 'POST':
        username = request.form.get('username')
        mobile_number = request.form.get('mobile_number')
        
        if not username or username.strip() == '':
            flash('Username cannot be empty.', 'danger')
            return render_template('user_profile_settings.html')

        # Check if username is already taken by another user
        existing_user = User.query.filter(
            User.username == username.strip(), 
            User.id != current_user.id
        ).first()
        
        if existing_user:
            flash('Username already taken. Please choose another one.', 'danger')
            return render_template('user_profile_settings.html')
        
        current_user.username = username.strip()
        current_user.mobile_number = mobile_number
        
        # Handle profile picture upload
        profile_pic = request.files.get('profile_picture')
        if profile_pic and profile_pic.filename != '': # Check if a file was actually provided
            # Delete old profile picture ONLY if it's a local file and not a default or remote URL
            if (current_user.profile_pic and 
                not current_user.profile_pic.endswith('default_avatar.png') and
                not current_user.profile_pic.startswith('http')):
                try:
                    full_old_pic_path = os.path.join(app.static_folder, current_user.profile_pic)
                    if os.path.exists(full_old_pic_path):
                        os.remove(full_old_pic_path)
                except Exception as e:
                    print(f"Error deleting old profile pic {current_user.profile_pic}: {e}")
            
            # Save new profile picture
            image_path = save_file(profile_pic)
            if image_path:
                current_user.profile_pic = image_path
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('user_profile_settings'))
    
    return render_template('user_profile_settings.html')

# Admin routes
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    pending_products = Product.query.filter_by(status='pending').all()
    all_products = Product.query.order_by(Product.created_at.desc()).all()
    all_users = User.query.order_by(User.created_at.desc()).all()
    
    return render_template('admin_panel.html',
                         pending_products=pending_products,
                         all_products=all_products,
                         all_users=all_users)

@app.route('/admin/product/<int:product_id>/<action>', methods=['POST'])
@admin_required
def admin_product_action(product_id, action):
    product = Product.query.get_or_404(product_id)
    
    if action == 'accept':
        product.status = 'accepted'
        flash(f'Product "{product.name}" has been accepted.', 'success')
    elif action == 'reject':
        product.status = 'rejected'
        flash(f'Product "{product.name}" has been rejected.', 'warning')
    elif action == 'delete':
        for image in list(product.images): # Iterate over a copy for safe deletion
            try:
                full_image_path = os.path.join(app.static_folder, image.image_url)
                if os.path.exists(full_image_path):
                    os.remove(full_image_path)
                db.session.delete(image)
            except Exception as e:
                print(f"Error deleting image file {image.image_url}: {e}")
        
        # Explicitly delete related entities
        Cart.query.filter_by(product_id=product_id).delete()
        Favorite.query.filter_by(product_id=product_id).delete()
        Comment.query.filter_by(product_id=product_id).delete()

        db.session.delete(product)
        flash(f'Product "{product.name}" has been deleted.', 'success')
    else:
        flash('Invalid action.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/modify/<int:product_id>')
@admin_required
def admin_modify_product(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_create.html', 
                         product=product, 
                         images=product.images,
                         categories=get_categories(),
                         is_admin_edit=True,
                         statuses=['pending', 'accepted', 'rejected'])

@app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.is_admin:
        flash('Cannot delete admin users.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    for product in list(user.products): # Iterate over a copy of the list of products for this user
        for image in list(product.images): # Iterate over a copy of images for each product
            try:
                full_image_path = os.path.join(app.static_folder, image.image_url)
                if os.path.exists(full_image_path):
                    os.remove(full_image_path)
                db.session.delete(image)
            except Exception as e:
                print(f"Error deleting image file {image.image_url} for user {user.username}: {e}")
        
        # Explicitly delete related entities
        Cart.query.filter_by(product_id=product.id).delete()
        Favorite.query.filter_by(product_id=product.id).delete()
        Comment.query.filter_by(product_id=product.id).delete()
        
        db.session.delete(product) # Delete the product itself
    
    # Delete user's profile picture if it exists and is not a default or remote Google URL
    if (user.profile_pic and 
        not user.profile_pic.endswith('default_avatar.png') and
        not user.profile_pic.startswith('http')):
        try:
            full_user_pic_path = os.path.join(app.static_folder, user.profile_pic)
            if os.path.exists(full_user_pic_path):
                os.remove(full_user_pic_path)
        except Exception as e:
            print(f"Error deleting user profile pic {user.profile_pic} for user {user.username}: {e}")
    
    db.session.delete(user) # Delete the user
    db.session.commit()
    
    flash(f'User "{user.username}" and all their products have been deleted.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/google/login')
def google_login():
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/google/callback')
def google_callback():
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo') or token.get('id_token')

        google_id = user_info['sub']
        email = user_info['email']
        name = user_info['name']
        profile_pic = user_info.get('picture', url_for('static', filename='img/default_avatar.png'))

        user = User.query.filter_by(google_id=google_id).first()

        if not user:
            username = email.split('@')[0]
            counter = 1
            original_username = username
            while User.query.filter_by(username=username).first():
                username = f"{original_username}{counter}"
                counter += 1

            user = User(
                google_id=google_id,
                email=email,
                name=name,
                username=username,
                profile_pic=profile_pic,
                mobile_number='', 
                is_admin=False
            )
            db.session.add(user)
            db.session.commit()

        login_user(user)
        flash(f'Welcome back, {user.name}!', 'success')
        return redirect(url_for('index'))

    except Exception as e:
        import traceback
        print("❌ Google Login Error:", e)
        traceback.print_exc()
        flash('Google login failed. Please try again.', 'danger')
        return redirect(url_for('login'))

@app.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    
    if product.seller_id == current_user.id:
        flash('You cannot add your own product to the cart.', 'danger')
        return redirect(request.referrer or url_for('product_detail', product_id=product_id))
    
    if product.status != 'accepted':
        flash('This product is not available for purchase.', 'danger')
        return redirect(request.referrer or url_for('product_detail', product_id=product_id))

    cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if cart_item:
        cart_item.quantity += 1
        flash(f'Quantity of "{product.name}" in cart increased to {cart_item.quantity}!', 'success')
    else:
        cart_item = Cart(user_id=current_user.id, product_id=product_id, quantity=1)
        db.session.add(cart_item)
        flash(f'Product "{product.name}" added to cart!', 'success')
    
    db.session.commit()
    return redirect(request.referrer or url_for('index'))

@app.route('/cart/remove/<int:cart_id>', methods=['POST'])
@login_required
def remove_from_cart(cart_id):
    cart_item = Cart.query.get_or_404(cart_id)
    
    if cart_item.user_id != current_user.id:
        abort(403)
    
    product_name = cart_item.product.name if cart_item.product else 'Unknown Product'
    db.session.delete(cart_item)
    db.session.commit()
    flash(f'Product "{product_name}" removed from cart!', 'success')
    return redirect(url_for('view_cart'))

@app.route('/cart')
# Removed @login_required to allow anonymous access to the cart view.
# The internal logic below handles whether user is authenticated.
def view_cart():
    cart_items = []
    total = 0

    if current_user.is_authenticated:
        raw_cart_items = Cart.query.filter_by(user_id=current_user.id).all()
        
        # Filter out cart items where the product might have been deleted or unaccepted
        # This also helps keep the cart clean on load.
        cleaned_cart_items = []
        for item in list(raw_cart_items): # Iterate over a copy to modify original
            if item.product and item.product.status == 'accepted':
                cleaned_cart_items.append(item)
            else:
                product_name = item.product.name if item.product else f"ID: {item.product_id or 'UNKNOWN'}"
                flash(f"'{product_name}' was unavailable or unaccepted and has been removed from your cart.", 'warning')
                db.session.delete(item)
        db.session.commit() # Commit deletions
        cart_items = cleaned_cart_items
        total = sum(item.product.price * item.quantity for item in cart_items if item.product) 
    else:
        # Handle case for anonymous users
        flash("You need to log in to manage your persistent cart. For now, enjoy the emptiness.", 'info')

    return render_template('cart.html', cart_items=cart_items, total=total)

# Checkout page
@app.route('/checkout')
@login_required # Checkout still requires authentication for practical reasons
def checkout():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    
    # Remove any cart items whose products are no longer available or accepted
    # This ensures only viable products are displayed for checkout contact.
    cleaned_cart_items = []
    has_unavailable_items = False
    for item in list(cart_items): # Iterate over a copy to modify list safely
        if item.product and item.product.status == 'accepted':
            cleaned_cart_items.append(item)
        else:
            has_unavailable_items = True
            product_name = item.product.name if item.product else f"ID: {item.product_id or 'UNKNOWN'}"
            flash(f"'{product_name}' was unavailable or unaccepted and has been removed from your cart for checkout.", 'warning')
            db.session.delete(item)
    db.session.commit() # Commit any removals
    
    # After cleaning, update the list being used
    cart_items = cleaned_cart_items


    if not cart_items: # Re-check after cleaning
        flash('Your cart is empty. Nothing to checkout, you idiot!', 'danger')
        return redirect(url_for('index'))

    # Group items by seller for easier contact
    sellers_and_products = {}
    for item in cart_items:
        if item.product and item.product.seller:
            seller = item.product.seller
            if seller.id not in sellers_and_products:
                sellers_and_products[seller.id] = {
                    'seller_info': seller,
                    'products': []
                }
            sellers_and_products[seller.id]['products'].append(item)
        # No else needed here for items without product/seller, as they were cleaned above.

    return render_template('checkout.html', sellers_and_products=sellers_and_products)


@app.route('/favorites/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_favorites(product_id):
    product = Product.query.get_or_404(product_id)

    if product.seller_id == current_user.id:
        flash('You cannot add your own product to favorites.', 'danger')
        return redirect(request.referrer or url_for('product_detail', product_id=product_id))

    if product.status != 'accepted':
        flash('This product is not available to be favorited.', 'danger')
        return redirect(request.referrer or url_for('product_detail', product_id=product_id))
    
    favorite = Favorite.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if not favorite:
        favorite = Favorite(user_id=current_user.id, product_id=product_id)
        db.session.add(favorite)
        db.session.commit()
        flash(f'Product "{product.name}" added to favorites!', 'success')
    else:
        flash(f'Product "{product.name}" is already in your favorites!', 'info')
    
    return redirect(request.referrer or url_for('index'))

@app.route('/favorites/remove/<int:favorite_id>', methods=['POST'])
@login_required
def remove_from_favorites(favorite_id):
    favorite = Favorite.query.get_or_404(favorite_id)
    
    if favorite.user_id != current_user.id:
        abort(403)
    
    product_name = favorite.product.name if favorite.product else 'Unknown Product'
    db.session.delete(favorite)
    db.session.commit()
    flash(f'Product "{product_name}" removed from favorites!', 'success')
    return redirect(url_for('view_favorites'))

@app.route('/favorites')
# Removed @login_required to allow anonymous access to the favorites view.
# The internal logic below handles whether user is authenticated.
def view_favorites():
    favorites = []
    
    if current_user.is_authenticated:
        raw_favorites = Favorite.query.filter_by(user_id=current_user.id).all()
        
        # Filter out favorite items where the product might have been deleted or unaccepted
        cleaned_favorites = []
        for item in list(raw_favorites): # Iterate over a copy
            if item.product and item.product.status == 'accepted':
                cleaned_favorites.append(item)
            else:
                product_name = item.product.name if item.product else f"ID: {item.product_id or 'UNKNOWN'}"
                flash(f"'{product_name}' was unavailable or unaccepted and has been removed from your favorites.", 'warning')
                db.session.delete(item)
        db.session.commit() # Commit deletions
        favorites = cleaned_favorites
    else:
        # Handle case for anonymous users
        flash("You need to log in to manage your favorites. This list is a barren wasteland without you.", 'info')

    return render_template('favorites.html', favorites=favorites)

@app.route('/product/<int:product_id>/comment', methods=['POST'])
@login_required
def add_comment(product_id):
    product = Product.query.get_or_404(product_id)
    content = request.form.get('content')
    
    if not content or content.strip() == '':
        flash('Comment cannot be empty!', 'danger')
        return redirect(url_for('product_detail', product_id=product_id))
    
    comment = Comment(
        content=content.strip(),
        user_id=current_user.id,
        product_id=product_id
    )
    
    db.session.add(comment)
    db.session.commit()
    
    flash('Comment added successfully!', 'success')
    return redirect(url_for('product_detail', product_id=product_id))

@app.route('/comment/delete/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    
    if comment.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    product_id_to_redirect = comment.product_id
    db.session.delete(comment)
    db.session.commit()
    
    flash('Comment deleted successfully!', 'success')
    return redirect(url_for('product_detail', product_id=product_id_to_redirect))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('403.html'), 403

# Create database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)