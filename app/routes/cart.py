from flask import Blueprint, jsonify, request, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models1 import CartItem, Product, Order, OrderDetail, Invoice, InvoiceItem, User
from datetime import datetime

cart_bp = Blueprint('cart', __name__, url_prefix='/cart')

@cart_bp.route('/')
@login_required
def view_cart():
    try:
        cart_items = current_user.get_cart()
        total = 0
        cart_data = []
        
        for item in cart_items:
            if item.product:
                product_total = float(item.product.price) * item.quantity
                total += product_total
                
                cart_data.append({
                    'id': item.idCartItem,
                    'product_id': item.product.idProduct,
                    'name': item.product.nameProduct,
                    'price': float(item.product.price),
                    'quantity': item.quantity,
                    'image': item.product.image,
                    'subtotal': product_total
                })
            else:
                # Si el producto fue eliminado, elimina el item del carrito
                db.session.delete(item)
                db.session.commit()
        
        return render_template('cart.html', cart_items=cart_data, total=total)
    
    except Exception as e:
        print(f"Error en view_cart: {str(e)}")
        flash('Error al cargar el carrito', 'danger')
        return render_template('cart.html', cart_items=[], total=0)

@cart_bp.route('/api/add', methods=['POST'])
@login_required
def add_to_cart():
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)
        
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'success': False, 'message': 'Producto no encontrado'})
        
        existing_item = CartItem.query.filter_by(
            idUser=current_user.idUser, 
            idProduct=product_id
        ).first()
        
        if existing_item:
            if existing_item.quantity + quantity > product.stock:
                return jsonify({'success': False, 'message': 'No hay suficiente stock disponible'})
            
            existing_item.quantity += quantity
        else:
            if quantity > product.stock:
                return jsonify({'success': False, 'message': 'No hay suficiente stock disponible'})
            
            new_item = CartItem(
                idUser=current_user.idUser,
                idProduct=product_id,
                quantity=quantity
            )
            db.session.add(new_item)
        
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': 'Producto agregado al carrito',
            'cart_count': current_user.get_cart_count()
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"Error en add_to_cart: {str(e)}")
        return jsonify({'success': False, 'message': 'Error al agregar al carrito: ' + str(e)})

@cart_bp.route('/api/update', methods=['POST'])
@login_required
def update_cart_item():
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        quantity = data.get('quantity')
        
        if quantity <= 0:
            return remove_from_cart()
        
        item = CartItem.query.get(item_id)
        if item and item.idUser == current_user.idUser:
            if quantity > item.product.stock:
                return jsonify({'success': False, 'message': 'No hay suficiente stock disponible'})
            
            item.quantity = quantity
            db.session.commit()
            return jsonify({'success': True, 'message': 'Carrito actualizado'})
        
        return jsonify({'success': False, 'message': 'Item no encontrado'})
    
    except Exception as e:
        db.session.rollback()
        print(f"Error en update_cart_item: {str(e)}")
        return jsonify({'success': False, 'message': 'Error al actualizar el carrito'})

@cart_bp.route('/api/remove', methods=['POST'])
@login_required
def remove_from_cart():
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        
        item = CartItem.query.get(item_id)
        if item and item.idUser == current_user.idUser:
            db.session.delete(item)
            db.session.commit()
            return jsonify({
                'success': True, 
                'message': 'Producto eliminado del carrito',
                'cart_count': current_user.get_cart_count()
            })
        
        return jsonify({'success': False, 'message': 'Item no encontrado'})
    
    except Exception as e:
        db.session.rollback()
        print(f"Error en remove_from_cart: {str(e)}")
        return jsonify({'success': False, 'message': 'Error al eliminar el producto'})

@cart_bp.route('/api/clear', methods=['POST'])
@login_required
def clear_cart():
    try:
        CartItem.query.filter_by(idUser=current_user.idUser).delete()
        db.session.commit()
        return jsonify({'success': True, 'message': 'Carrito vaciado'})
    
    except Exception as e:
        db.session.rollback()
        print(f"Error en clear_cart: {str(e)}")
        return jsonify({'success': False, 'message': 'Error al vaciar el carrito'})

@cart_bp.route('/api/count')
@login_required
def get_cart_count():
    try:
        count = current_user.get_cart_count()
        return jsonify({'success': True, 'count': count})
    
    except Exception as e:
        return jsonify({'success': False, 'count': 0})

# =============================================
# RUTAS PARA PEDIDOS
# =============================================

@cart_bp.route('/api/create_cash_order', methods=['POST'])
@login_required
def create_cash_order():
    try:
        data = request.get_json()
        shipping_address = data.get('shipping_address', 'Dirección por confirmar')
        
        cart_items = current_user.get_cart()
        if not cart_items:
            return jsonify({'success': False, 'message': 'El carrito está vacío'})
        
        total = 0
        order_details = []
        
        for item in cart_items:
            if not item.product:
                continue
                
            if item.quantity > item.product.stock:
                return jsonify({
                    'success': False, 
                    'message': f'No hay suficiente stock de {item.product.nameProduct}. Stock disponible: {item.product.stock}'
                })
            
            item_total = float(item.product.price) * item.quantity
            total += item_total
            
            order_details.append({
                'product': item.product,
                'quantity': item.quantity,
                'price': float(item.product.price)
            })
        
        # Crear orden
        new_order = Order(
            idUser=current_user.idUser,
            totalAmount=total,
            status='Pendiente',
            payment_method='Efectivo',
            items_count=len(order_details),
            orderDate=datetime.utcnow()
        )
        
        db.session.add(new_order)
        db.session.flush()
        
        # Crear detalles de orden
        for detail in order_details:
            order_detail = OrderDetail(
                idOrder=new_order.idOrder,
                idProduct=detail['product'].idProduct,
                quantity=detail['quantity'],
                price=detail['price']
            )
            db.session.add(order_detail)
            
            # Actualizar stock
            detail['product'].stock -= detail['quantity']
        
        # Crear factura
        invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{new_order.idOrder:04d}"
        
        new_invoice = Invoice(
            invoice_number=invoice_number,
            invoice_date=datetime.utcnow(),
            customer_name=current_user.nameUser,
            customer_email=current_user.emailUser,
            customer_id=str(current_user.idUser),
            payment_method='Efectivo',
            payment_details='Pago al recibir el pedido',
            subtotal=total,
            taxes=0,
            total_amount=total,
            status='Activa'
        )
        
        db.session.add(new_invoice)
        db.session.flush()
        
        # Items de factura
        for detail in order_details:
            invoice_item = InvoiceItem(
                idInvoice=new_invoice.idInvoice,
                idProduct=detail['product'].idProduct,
                product_name=detail['product'].nameProduct,
                product_price=detail['price'],
                quantity=detail['quantity'],
                subtotal=detail['price'] * detail['quantity']
            )
            db.session.add(invoice_item)
        
        # Limpiar carrito
        CartItem.query.filter_by(idUser=current_user.idUser).delete()
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Pedido creado exitosamente. Pagarás al recibir tu compra.',
            'order_id': new_order.idOrder,
            'invoice_number': invoice_number,
            'total': total
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error en create_cash_order: {str(e)}")
        return jsonify({'success': False, 'message': 'Error al crear el pedido: ' + str(e)})

@cart_bp.route('/api/create_card_order', methods=['POST'])
@login_required
def create_card_order():
    try:
        data = request.get_json()
        payment_details = data.get('payment_details', {})
        
        cart_items = current_user.get_cart()
        if not cart_items:
            return jsonify({'success': False, 'message': 'El carrito está vacío'})
        
        total = 0
        order_details = []
        
        for item in cart_items:
            if not item.product:
                continue
                
            if item.quantity > item.product.stock:
                return jsonify({
                    'success': False, 
                    'message': f'No hay suficiente stock de {item.product.nameProduct}'
                })
            
            item_total = float(item.product.price) * item.quantity
            total += item_total
            
            order_details.append({
                'product': item.product,
                'quantity': item.quantity,
                'price': float(item.product.price)
            })
        
        # Crear orden
        new_order = Order(
            idUser=current_user.idUser,
            totalAmount=total,
            status='Completado',
            payment_method='Tarjeta',
            items_count=len(order_details),
            orderDate=datetime.utcnow()
        )
        
        db.session.add(new_order)
        db.session.flush()
        
        # Detalles de orden
        for detail in order_details:
            order_detail = OrderDetail(
                idOrder=new_order.idOrder,
                idProduct=detail['product'].idProduct,
                quantity=detail['quantity'],
                price=detail['price']
            )
            db.session.add(order_detail)
            detail['product'].stock -= detail['quantity']
        
        # Factura
        invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{new_order.idOrder:04d}"
        
        new_invoice = Invoice(
            invoice_number=invoice_number,
            invoice_date=datetime.utcnow(),
            customer_name=current_user.nameUser,
            customer_email=current_user.emailUser,
            customer_id=str(current_user.idUser),
            payment_method='Tarjeta',
            payment_details=f"Tarjeta terminada en {payment_details.get('last_digits', '****')}",
            subtotal=total,
            taxes=0,
            total_amount=total,
            status='Activa'
        )
        
        db.session.add(new_invoice)
        db.session.flush()
        
        # Items de factura
        for detail in order_details:
            invoice_item = InvoiceItem(
                idInvoice=new_invoice.idInvoice,
                idProduct=detail['product'].idProduct,
                product_name=detail['product'].nameProduct,
                product_price=detail['price'],
                quantity=detail['quantity'],
                subtotal=detail['price'] * detail['quantity']
            )
            db.session.add(invoice_item)
        
        # Limpiar carrito
        CartItem.query.filter_by(idUser=current_user.idUser).delete()
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Pago con tarjeta procesado exitosamente',
            'order_id': new_order.idOrder,
            'invoice_number': invoice_number,
            'total': total
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error en create_card_order: {str(e)}")
        return jsonify({'success': False, 'message': 'Error al procesar el pago: ' + str(e)})

@cart_bp.route('/api/create_pse_order', methods=['POST'])
@login_required
def create_pse_order():
    try:
        data = request.get_json()
        bank = data.get('bank', '')
        email = data.get('email', '')
        
        cart_items = current_user.get_cart()
        if not cart_items:
            return jsonify({'success': False, 'message': 'El carrito está vacío'})
        
        total = 0
        order_details = []
        
        for item in cart_items:
            if not item.product:
                continue
                
            if item.quantity > item.product.stock:
                return jsonify({
                    'success': False, 
                    'message': f'No hay suficiente stock de {item.product.nameProduct}'
                })
            
            item_total = float(item.product.price) * item.quantity
            total += item_total
            
            order_details.append({
                'product': item.product,
                'quantity': item.quantity,
                'price': float(item.product.price)
            })
        
        # Crear orden
        new_order = Order(
            idUser=current_user.idUser,
            totalAmount=total,
            status='Procesando',
            payment_method='PSE',
            items_count=len(order_details),
            orderDate=datetime.utcnow()
        )
        
        db.session.add(new_order)
        db.session.flush()
        
        # Detalles de orden
        for detail in order_details:
            order_detail = OrderDetail(
                idOrder=new_order.idOrder,
                idProduct=detail['product'].idProduct,
                quantity=detail['quantity'],
                price=detail['price']
            )
            db.session.add(order_detail)
            detail['product'].stock -= detail['quantity']
        
        # Factura
        invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{new_order.idOrder:04d}"
        
        new_invoice = Invoice(
            invoice_number=invoice_number,
            invoice_date=datetime.utcnow(),
            customer_name=current_user.nameUser,
            customer_email=email or current_user.emailUser,
            customer_id=str(current_user.idUser),
            payment_method='PSE',
            payment_details=f'Banco: {bank}',
            subtotal=total,
            taxes=0,
            total_amount=total,
            status='Activa'
        )
        
        db.session.add(new_invoice)
        db.session.flush()
        
        # Items de factura
        for detail in order_details:
            invoice_item = InvoiceItem(
                idInvoice=new_invoice.idInvoice,
                idProduct=detail['product'].idProduct,
                product_name=detail['product'].nameProduct,
                product_price=detail['price'],
                quantity=detail['quantity'],
                subtotal=detail['price'] * detail['quantity']
            )
            db.session.add(invoice_item)
        
        # Limpiar carrito
        CartItem.query.filter_by(idUser=current_user.idUser).delete()
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Pedido con PSE creado exitosamente',
            'order_id': new_order.idOrder,
            'invoice_number': invoice_number,
            'total': total
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error en create_pse_order: {str(e)}")
        return jsonify({'success': False, 'message': 'Error al crear el pedido PSE: ' + str(e)})

@cart_bp.route('/order/confirmation')
@login_required
def order_confirmation():
    try:
        order_id = request.args.get('order_id')
        if not order_id:
            flash('No se especificó el pedido', 'danger')
            return redirect(url_for('cart.view_cart'))
        
        order = Order.query.get(order_id)
        
        if not order or order.idUser != current_user.idUser:
            flash('Pedido no encontrado', 'danger')
            return redirect(url_for('cart.view_cart'))
        
        # Obtener método de pago de la factura
        invoice = Invoice.query.filter_by(customer_id=str(current_user.idUser)).order_by(Invoice.invoice_date.desc()).first()
        payment_method = invoice.payment_method if invoice else 'Efectivo'
        
        return render_template('order_confirmation.html', 
                             order=order, 
                             payment_method=payment_method)
    
    except Exception as e:
        print(f"Error en order_confirmation: {str(e)}")
        flash('Error al cargar la confirmación del pedido', 'danger')
        return redirect(url_for('cart.view_cart'))

@cart_bp.route('/api/user/orders')
@login_required
def get_user_orders():
    try:
        orders = Order.query.filter_by(idUser=current_user.idUser)\
                          .order_by(Order.orderDate.desc())\
                          .all()
        
        orders_data = []
        for order in orders:
            items_count = OrderDetail.query.filter_by(idOrder=order.idOrder).count()
            
            orders_data.append({
                'id': order.idOrder,
                'total': float(order.totalAmount),
                'status': order.status,
                'date': order.orderDate.strftime('%d/%m/%Y %H:%M'),
                'items_count': items_count
            })
        
        return jsonify({'success': True, 'orders': orders_data})
    
    except Exception as e:
        print(f"Error en get_user_orders: {str(e)}")
        return jsonify({'success': False, 'message': 'Error al cargar las órdenes: ' + str(e)})

@cart_bp.route('/api/order/<int:order_id>')
@login_required
def get_order_details(order_id):
    try:
        order = Order.query.get(order_id)
        
        if not order or order.idUser != current_user.idUser:
            return jsonify({'success': False, 'message': 'Pedido no encontrado'})
        
        order_details = OrderDetail.query.filter_by(idOrder=order_id).all()
        
        details_data = []
        for detail in order_details:
            details_data.append({
                'product_name': detail.product.nameProduct if detail.product else 'Producto no disponible',
                'quantity': detail.quantity,
                'price': float(detail.price),
                'subtotal': float(detail.price) * detail.quantity
            })
        
        order_data = {
            'id': order.idOrder,
            'total': float(order.totalAmount),
            'status': order.status,
            'date': order.orderDate.strftime('%d/%m/%Y %H:%M'),
            'details': details_data
        }
        
        return jsonify({'success': True, 'order': order_data})
    
    except Exception as e:
        print(f"Error en get_order_details: {str(e)}")
        return jsonify({'success': False, 'message': 'Error al cargar el pedido: ' + str(e)})