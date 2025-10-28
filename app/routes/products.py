from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from app import db
from app.models1 import Product
from decimal import Decimal
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os

products_bp = Blueprint('products', __name__)

@products_bp.route('/api/products', methods=['GET'])
def get_products():
    """Obtener todos los productos activos (API JSON)"""
    try:
        # OBTENER TODOS LOS PRODUCTOS ACTIVOS SIN LÍMITE
        products = Product.query.filter_by(status='Activo').all()
        return jsonify([{
            'id': product.idProduct,
            'name': product.nameProduct,
            'description': product.description or '',
            'price': float(product.price),
            'image_url': product.image or f'https://via.placeholder.com/250x300/f8f9fa/000?text={product.nameProduct}',
            'category': product.category,
            'stock': product.stock,
            'status': product.status,
            'details': getattr(product, 'details', '')  # Detalles adicionales si existen
        } for product in products])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ✅ NUEVA RUTA: Página HTML de productos por categoría
@products_bp.route('/categoria/<category_name>')
def category_products_page(category_name):
    """Página HTML de productos por categoría"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 30
        
        # Filtrar productos por categoría (case insensitive)
        products_query = Product.query.filter(
            Product.category.ilike(f'%{category_name}%'),
            Product.status == 'Activo'
        )
        
        pagination = products_query.paginate(
            page=page, 
            per_page=per_page,
            error_out=False
        )
        
        products = pagination.items
        
        # Convertir productos a formato para la template
        products_data = []
        for product in products:
            products_data.append({
                'id': product.idProduct,
                'name': product.nameProduct,
                'description': product.description or '',
                'price': float(product.price),
                'image_url': product.image or f'https://via.placeholder.com/300x400/f8f9fa/000?text={product.nameProduct}',
                'category': product.category,
                'stock': product.stock,
                'status': product.status
            })
        
        return render_template('category_products.html', 
                             products=products_data,
                             category_name=category_name,
                             current_page=page,
                             total_pages=pagination.pages,
                             has_next=pagination.has_next,
                             has_prev=pagination.has_prev)
                             
    except Exception as e:
        return render_template('error404.html'), 404

@products_bp.route('/product/<int:product_id>')  # ← CAMBIADO de 'producto' a 'product'
def product_detail(product_id):
    """Página de detalles del producto (HTML)"""
    try:
        product = Product.query.get_or_404(product_id)
        
        # Convertir producto a formato para la template
        product_data = {
            'id': product.idProduct,
            'name': product.nameProduct,
            'description': product.description or '',
            'price': float(product.price),
            'image_url': product.image or f'https://via.placeholder.com/500x600/f8f9fa/000?text={product.nameProduct}',
            'category': product.category,
            'stock': product.stock,
            'status': product.status,
            'details': getattr(product, 'details', ''),
            'size': getattr(product, 'size', 'No especificado'),
            'color': getattr(product, 'color', 'No especificado')
        }
        
        # Productos relacionados (misma categoría)
        related_products = Product.query.filter(
            Product.category == product.category,
            Product.idProduct != product_id,
            Product.status == 'Activo'
        ).limit(4).all()
        
        # Convertir productos relacionados
        related_products_data = []
        for related_product in related_products:
            related_products_data.append({
                'id': related_product.idProduct,
                'name': related_product.nameProduct,
                'price': float(related_product.price),
                'image_url': related_product.image or f'https://via.placeholder.com/250x300/f8f9fa/000?text={related_product.nameProduct}',
                'category': related_product.category
            })
        
        return render_template('product_detail.html', 
                             product=product_data, 
                             related_products=related_products_data)
    except Exception as e:
        return render_template('error404.html'), 404

@products_bp.route('/api/products/<int:product_id>', methods=['GET'])
def get_product_detail_api(product_id):
    """Obtener detalles específicos de un producto (API JSON)"""
    try:
        product = Product.query.get_or_404(product_id)
        return jsonify({
            'id': product.idProduct,
            'name': product.nameProduct,
            'description': product.description or '',
            'price': float(product.price),
            'image_url': product.image or f'https://via.placeholder.com/300x300/f8f9fa/000?text={product.nameProduct}',
            'category': product.category,
            'stock': product.stock,
            'status': product.status,
            'details': getattr(product, 'details', ''),
            'size': getattr(product, 'size', 'No especificado'),
            'color': getattr(product, 'color', 'No especificado')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/products/category/<category_name>', methods=['GET'])
def get_products_by_category(category_name):
    """Obtener productos por categoría (API JSON)"""
    try:
        products = Product.query.filter_by(
            category=category_name, 
            status='Activo'
        ).all()
        
        return jsonify([{
            'id': product.idProduct,
            'name': product.nameProduct,
            'description': product.description or '',
            'price': float(product.price),
            'image_url': product.image or f'https://via.placeholder.com/250x300/f8f9fa/000?text={product.nameProduct}',
            'category': product.category,
            'stock': product.stock,
            'status': product.status
        } for product in products])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/products', methods=['POST'])
@login_required
def add_product():
    """Agregar nuevo producto"""
    try:
        # Verificar si es JSON o form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
            # Convertir tipos de datos para form data
            if 'price' in data:
                data['price'] = float(data['price'])
            if 'stock' in data:
                data['stock'] = int(data['stock'])
        
        # Validar campos requeridos
        required_fields = ['name', 'category', 'price', 'stock']
        missing_fields = [field for field in required_fields if field not in data or not data[field]]
        
        if missing_fields:
            return jsonify({
                'success': False, 
                'message': f'Campos requeridos faltantes: {", ".join(missing_fields)}'
            }), 400
        
        # Validar tipos de datos
        try:
            price = float(data['price'])
            stock = int(data['stock'])
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'message': 'Precio y stock deben ser valores numéricos'
            }), 400
        
        new_product = Product(
            nameProduct=data['name'],
            category=data['category'],
            price=price,
            stock=stock,
            description=data.get('description', ''),
            image=data.get('image', ''),
            status='Activo' if stock > 0 else 'Inactivo'
        )
        
        # Añadir campos adicionales si existen en el modelo
        if hasattr(Product, 'details') and 'details' in data:
            new_product.details = data['details']
        if hasattr(Product, 'size') and 'size' in data:
            new_product.size = data['size']
        if hasattr(Product, 'color') and 'color' in data:
            new_product.color = data['color']
        
        db.session.add(new_product)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Producto agregado correctamente',
            'product': {
                'id': new_product.idProduct,
                'name': new_product.nameProduct
            }
        }), 201  # Código 201 para creado
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error al agregar el producto: {str(e)}'
        }), 500

@products_bp.route('/api/products/<int:product_id>', methods=['PUT'])
@login_required
def update_product(product_id):
    """Actualizar producto existente"""
    try:
        product = Product.query.get_or_404(product_id)
        
        # Verificar si es JSON o form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
            # Convertir tipos de datos para form data
            if 'price' in data:
                data['price'] = float(data['price'])
            if 'stock' in data:
                data['stock'] = int(data['stock'])
        
        # Validar campos
        if 'name' in data:
            product.nameProduct = data['name']
        if 'category' in data:
            product.category = data['category']
        if 'price' in data:
            try:
                product.price = float(data['price'])
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'El precio debe ser un valor numérico'
                }), 400
        if 'stock' in data:
            try:
                product.stock = int(data['stock'])
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'El stock debe ser un valor numérico'
                }), 400
        
        if 'description' in data:
            product.description = data['description']
        if 'image' in data:
            product.image = data['image']
        
        # Actualizar campos adicionales si existen
        if hasattr(product, 'details') and 'details' in data:
            product.details = data['details']
        if hasattr(product, 'size') and 'size' in data:
            product.size = data['size']
        if hasattr(product, 'color') and 'color' in data:
            product.color = data['color']
        
        # Actualizar estado basado en stock
        product.status = 'Activo' if product.stock > 0 else 'Inactivo'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Producto actualizado correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error al actualizar el producto: {str(e)}'
        }), 500

@products_bp.route('/api/products/<int:product_id>', methods=['DELETE'])
@login_required
def delete_product(product_id):
    """Eliminar producto"""
    try:
        product = Product.query.get_or_404(product_id)
        db.session.delete(product)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Producto eliminado correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error al eliminar el producto: {str(e)}'
        }), 500

# ✅ NUEVA RUTA: Búsqueda de productos
@products_bp.route('/buscar')
def search_products():
    """Búsqueda de productos"""
    try:
        query = request.args.get('q', '')
        page = request.args.get('page', 1, type=int)
        per_page = 30
        
        if not query:
            return render_template('search_results.html', 
                                 products=[], 
                                 query=query,
                                 message='Ingresa un término de búsqueda')
        
        # Buscar productos que coincidan con el nombre o categoría
        products_query = Product.query.filter(
            db.or_(
                Product.nameProduct.ilike(f'%{query}%'),
                Product.category.ilike(f'%{query}%'),
                Product.description.ilike(f'%{query}%')
            ),
            Product.status == 'Activo'
        )
        
        pagination = products_query.paginate(
            page=page, 
            per_page=per_page,
            error_out=False
        )
        
        products = pagination.items
        
        # Convertir productos a formato para la template
        products_data = []
        for product in products:
            products_data.append({
                'id': product.idProduct,
                'name': product.nameProduct,
                'description': product.description or '',
                'price': float(product.price),
                'image_url': product.image or f'https://via.placeholder.com/300x400/f8f9fa/000?text={product.nameProduct}',
                'category': product.category,
                'stock': product.stock,
                'status': product.status
            })
        
        return render_template('search_results.html', 
                             products=products_data,
                             query=query,
                             current_page=page,
                             total_pages=pagination.pages,
                             has_next=pagination.has_next,
                             has_prev=pagination.has_prev)
                             
    except Exception as e:
        return render_template('error404.html'), 404

# =============================================================================
# NUEVAS RUTAS PARA FACTURACIÓN
# =============================================================================

# ✅ NUEVA RUTA: Búsqueda de productos para facturación
@products_bp.route('/api/products/search')
def search_products_api():
    """API para búsqueda de productos en facturación"""
    try:
        search_term = request.args.get('q', '')
        
        if not search_term:
            return jsonify([])
        
        # Buscar en la base de datos
        products = Product.query.filter(
            (Product.nameProduct.ilike(f'%{search_term}%')) |
            (Product.description.ilike(f'%{search_term}%')) |
            (Product.category.ilike(f'%{search_term}%'))
        ).filter(Product.status == 'Activo').limit(10).all()
        
        # Convertir a formato JSON
        products_data = []
        for product in products:
            products_data.append({
                'idProduct': product.idProduct,
                'nameProduct': product.nameProduct,
                'description': product.description,
                'price': float(product.price),
                'stock': product.stock,
                'category': product.category,
                'image': product.image
            })
        
        return jsonify(products_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ✅ NUEVA RUTA: Envío de factura por email
@products_bp.route('/send_invoice', methods=['POST'])
def send_invoice():
    """Enviar factura por email"""
    try:
        invoice_data = request.json
        
        # Renderizar template de factura
        html_content = render_template('invoice_email.html', 
                                     invoice=invoice_data,
                                     date=datetime.now().strftime('%d/%m/%Y'))
        
        # Configurar email
        msg = MIMEMultipart()
        msg['From'] = os.getenv('EMAIL_FROM', 'noreply.fashionboutique@gmail.com')
        msg['To'] = invoice_data['customer_email']
        msg['Subject'] = f"Factura {invoice_data['invoice_number']} - Fashion Boutique"
        
        msg.attach(MIMEText(html_content, 'html'))
        
        # Enviar email (usa tu configuración de email existente)
        # Comentado temporalmente para evitar errores de configuración
        # with smtplib.SMTP('smtp.gmail.com', 587) as server:
        #     server.starttls()
        #     server.login(os.getenv('EMAIL_USER'), os.getenv('EMAIL_PASS'))
        #     server.send_message(msg)
        
        # Por ahora solo simulamos el envío
        print(f"Simulando envío de factura a: {invoice_data['customer_email']}")
        
        return jsonify({'success': True, 'message': 'Factura enviada correctamente'})
        
    except Exception as e:
        print(f"Error en send_invoice: {str(e)}")
        return jsonify({'success': False, 'message': f'Error enviando email: {str(e)}'})

# ✅ NUEVA RUTA: Página de facturación
@products_bp.route('/facturacion')
@login_required  
def billing_page():
    return render_template('billing.html')  # ← Simple

# ✅ NUEVA RUTA: Obtener producto por ID para facturación
@products_bp.route('/api/products/billing/<int:product_id>', methods=['GET'])
def get_product_for_billing(product_id):
    """Obtener producto específico para facturación"""
    try:
        product = Product.query.get_or_404(product_id)
        return jsonify({
            'idProduct': product.idProduct,
            'nameProduct': product.nameProduct,
            'price': float(product.price),
            'stock': product.stock,
            'category': product.category,
            'image': product.image
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500