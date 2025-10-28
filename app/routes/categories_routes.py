# categories_routes.py
from flask import Blueprint, jsonify, request, flash, redirect, url_for, render_template
from flask_login import login_required, current_user
from app import db
from app.models1 import Category, Product, Subcategory
from app.decorators import admin_required

categories_bp = Blueprint('categories', __name__)

# =============================================================================
# RUTA PRINCIPAL PARA LA PÁGINA DE CATEGORÍAS
# =============================================================================

@categories_bp.route('/')
@login_required
@admin_required
def categories_page():
    """Página principal de gestión de categorías"""
    return render_template('categories.html')

# =============================================================================
# RUTAS PARA CATEGORÍAS (API)
# =============================================================================

@categories_bp.route('/api/categories', methods=['GET'])
def get_categories():
    try:
        categories = Category.query.all()
        
        categories_data = []
        for cat in categories:
            # Contar productos por categoría
            product_count = Product.query.filter_by(category=cat.nameCategory).count()
            
            # Obtener subcategorías
            subcategories = Subcategory.query.filter_by(idCategory=cat.idCategory).all()
            
            category_data = {
                'idCategory': cat.idCategory,
                'nameCategory': cat.nameCategory,
                'description': cat.description or '',
                'status': cat.status,
                'product_count': product_count,
                'subcategories': [sub.to_dict() for sub in subcategories]
            }
            
            categories_data.append(category_data)
        
        return jsonify({'success': True, 'categories': categories_data})
        
    except Exception as e:
        print(f"Error en /api/categories: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@categories_bp.route('/api/categories', methods=['POST'])
@login_required
@admin_required
def create_category():
    try:
        data = request.get_json()
        
        name_category = data.get('nameCategory')
        description = data.get('description', '')
        status = data.get('status', 'Activa')

        if not name_category:
            return jsonify({'success': False, 'error': 'El nombre de la categoría es requerido'}), 400

        # Verificar si la categoría ya existe
        existing_category = Category.query.filter_by(nameCategory=name_category).first()
        if existing_category:
            return jsonify({'success': False, 'error': 'Ya existe una categoría con este nombre'}), 400

        # Crear nueva categoría
        new_category = Category(
            nameCategory=name_category,
            description=description,
            status=status
        )

        db.session.add(new_category)
        db.session.commit()

        return jsonify({
            'success': True, 
            'message': 'Categoría creada correctamente',
            'category': {
                'idCategory': new_category.idCategory,
                'nameCategory': new_category.nameCategory,
                'description': new_category.description,
                'status': new_category.status
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error al crear categoría: {str(e)}'}), 500

@categories_bp.route('/api/categories/<int:category_id>', methods=['PUT'])
@login_required
@admin_required
def update_category(category_id):
    try:
        data = request.get_json()
        category = Category.query.get_or_404(category_id)
        
        # Actualizar campos
        if 'nameCategory' in data:
            category.nameCategory = data['nameCategory']
        if 'description' in data:
            category.description = data['description']
        if 'status' in data:
            category.status = data['status']
        
        db.session.commit()

        return jsonify({
            'success': True, 
            'message': 'Categoría actualizada correctamente',
            'category': {
                'idCategory': category.idCategory,
                'nameCategory': category.nameCategory,
                'description': category.description,
                'status': category.status
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error al actualizar categoría: {str(e)}'}), 500

@categories_bp.route('/api/categories/<int:category_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_category(category_id):
    try:
        category = Category.query.get_or_404(category_id)
        
        # Verificar si hay productos usando esta categoría
        product_count = Product.query.filter_by(category=category.nameCategory).count()
        if product_count > 0:
            return jsonify({
                'success': False, 
                'error': f'No se puede eliminar la categoría. Tiene {product_count} producto(s) asociado(s).'
            }), 400

        db.session.delete(category)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Categoría eliminada correctamente'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error al eliminar categoría: {str(e)}'}), 500

@categories_bp.route('/api/categories/<int:category_id>/status', methods=['PUT'])
@login_required
@admin_required
def toggle_category_status(category_id):
    try:
        category = Category.query.get_or_404(category_id)
        
        # Cambiar estado
        new_status = 'Inactiva' if category.status == 'Activa' else 'Activa'
        category.status = new_status
        
        db.session.commit()

        return jsonify({
            'success': True, 
            'message': f'Categoría {new_status.lower()} correctamente',
            'status': new_status
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error al cambiar estado: {str(e)}'}), 500

# =============================================================================
# RUTAS PARA SUBCATEGORÍAS (API)
# =============================================================================

@categories_bp.route('/api/subcategories', methods=['POST'])
@login_required
@admin_required
def create_subcategory():
    try:
        data = request.get_json()
        
        # Validar campos requeridos
        if not data.get('nameSubcategory'):
            return jsonify({'success': False, 'error': 'El nombre de la subcategoría es requerido'}), 400
        
        if not data.get('idCategory'):
            return jsonify({'success': False, 'error': 'La categoría padre es requerida'}), 400

        # Verificar si la categoría padre existe
        category = Category.query.get(data['idCategory'])
        if not category:
            return jsonify({'success': False, 'error': 'La categoría padre no existe'}), 404

        # Verificar si ya existe una subcategoría con el mismo nombre en esta categoría
        existing_subcategory = Subcategory.query.filter_by(
            idCategory=data['idCategory'],
            nameSubcategory=data['nameSubcategory']
        ).first()
        
        if existing_subcategory:
            return jsonify({'success': False, 'error': 'Ya existe una subcategoría con este nombre en esta categoría'}), 400

        # Crear nueva subcategoría
        new_subcategory = Subcategory(
            idCategory=data['idCategory'],
            nameSubcategory=data['nameSubcategory'],
            description=data.get('description', ''),
            status=data.get('status', 'Activa')
        )
        
        db.session.add(new_subcategory)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Subcategoría creada exitosamente',
            'subcategory': new_subcategory.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Error al crear subcategoría: {str(e)}'
        }), 500

@categories_bp.route('/api/categories/<int:category_id>/subcategories', methods=['GET'])
def get_subcategories_by_category(category_id):
    try:
        # Verificar si la categoría existe
        category = Category.query.get(category_id)
        if not category:
            return jsonify({'success': False, 'error': 'Categoría no encontrada'}), 404
        
        subcategories = Subcategory.query.filter_by(idCategory=category_id).all()
        
        return jsonify({
            'success': True,
            'subcategories': [sub.to_dict() for sub in subcategories]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error al cargar subcategorías: {str(e)}'
        }), 500

@categories_bp.route('/api/subcategories/<int:subcategory_id>/status', methods=['PUT'])
@login_required
@admin_required
def toggle_subcategory_status(subcategory_id):
    try:
        subcategory = Subcategory.query.get_or_404(subcategory_id)
        
        # Cambiar estado
        new_status = 'Inactiva' if subcategory.status == 'Activa' else 'Activa'
        subcategory.status = new_status
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Subcategoría {new_status.lower()} exitosamente',
            'status': new_status
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Error al cambiar estado: {str(e)}'
        }), 500

@categories_bp.route('/api/subcategories/<int:subcategory_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_subcategory(subcategory_id):
    try:
        subcategory = Subcategory.query.get_or_404(subcategory_id)
        
        # Verificar si hay productos usando esta subcategoría
        product_count = Product.query.filter_by(subcategory_id=subcategory_id).count()
        if product_count > 0:
            return jsonify({
                'success': False, 
                'error': f'No se puede eliminar la subcategoría. Tiene {product_count} producto(s) asociado(s).'
            }), 400
        
        db.session.delete(subcategory)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Subcategoría eliminada exitosamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Error al eliminar subcategoría: {str(e)}'
        }), 500

@categories_bp.route('/api/subcategories/<int:subcategory_id>', methods=['PUT'])
@login_required
@admin_required
def update_subcategory(subcategory_id):
    try:
        data = request.get_json()
        subcategory = Subcategory.query.get_or_404(subcategory_id)
        
        # Actualizar campos
        if 'nameSubcategory' in data:
            subcategory.nameSubcategory = data['nameSubcategory']
        if 'description' in data:
            subcategory.description = data['description']
        if 'status' in data:
            subcategory.status = data['status']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Subcategoría actualizada exitosamente',
            'subcategory': subcategory.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Error al actualizar subcategoría: {str(e)}'
        }), 500

# =============================================================================
# RUTAS PARA PÁGINAS PÚBLICAS
# =============================================================================

@categories_bp.route('/category/<category_name>')
def category_products_page(category_name):
    try:
        # Buscar la categoría
        category = Category.query.filter_by(
            nameCategory=category_name, 
            status='Activa'
        ).first()
        
        if not category:
            flash('Categoría no encontrada', 'error')
            return redirect(url_for('auth.home'))
        
        # Obtener productos de esta categoría
        products = Product.query.filter_by(
            category=category_name,
            status='Activo'
        ).all()
        
        return render_template('products.html', 
                             products=products, 
                             category_name=category_name,
                             title=f"Productos - {category_name}")
        
    except Exception as e:
        flash('Error al cargar la categoría', 'error')
        return redirect(url_for('auth.home'))

@categories_bp.route('/category/<category_name>/<subcategory_name>')
def subcategory_products_page(category_name, subcategory_name):
    try:
        # Buscar la subcategoría
        subcategory = Subcategory.query.filter_by(
            nameSubcategory=subcategory_name,
            status='Activa'
        ).first()
        
        if not subcategory:
            flash('Subcategoría no encontrada', 'error')
            return redirect(url_for('categories.category_products_page', category_name=category_name))
        
        # Obtener productos de esta subcategoría
        products = Product.query.filter_by(
            subcategory_id=subcategory.idSubcategory,
            status='Activo'
        ).all()
        
        return render_template('products.html', 
                             products=products, 
                             category_name=category_name,
                             subcategory_name=subcategory_name,
                             title=f"{subcategory_name} - {category_name}")
        
    except Exception as e:
        flash('Error al cargar la subcategoría', 'error')
        return redirect(url_for('categories.category_products_page', category_name=category_name))