# admin.py
from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from app import db, mail
from app.models1 import Order, User, Invoice, OrderDetail, Product
from datetime import datetime
import logging

# Configurar logging
logger = logging.getLogger(__name__)

# ✅ CORREGIDO: Agregar url_prefix para que todas las rutas empiecen con /admin
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    print(f"🔐 Usuario intentando acceder al dashboard: {current_user.nameUser}, is_admin: {current_user.is_admin}")
    
    if not current_user.is_admin:
        return "No autorizado", 403
    
    print("✅ Acceso al dashboard concedido")
    return render_template('admin_dashboard.html')

@admin_bp.route('/get_orders')
@login_required
def get_orders():
    try:
        print("🔍 Iniciando carga de pedidos...")
        print(f"👤 Usuario: {current_user.nameUser}, Admin: {current_user.is_admin}")
        
        # Verificar que el usuario es admin
        if not current_user.is_admin:
            print("❌ Usuario no es administrador")
            return jsonify({'success': False, 'message': 'No autorizado'}), 403
        
        print("✅ Usuario es administrador")
        
        # Obtener parámetros de filtro
        status_filter = request.args.get('status', 'all')
        payment_filter = request.args.get('payment', 'all')
        
        print(f"🎯 Filtros - Estado: {status_filter}, Pago: {payment_filter}")
        
        # Consulta base
        query = db.session.query(Order, User).join(User, Order.idUser == User.idUser)
        
        # Aplicar filtros
        if status_filter != 'all':
            query = query.filter(Order.status == status_filter)
        
        # Ordenar por fecha descendente
        orders_data = query.order_by(Order.orderDate.desc()).all()
        
        print(f"📦 Se encontraron {len(orders_data)} pedidos")
        
        orders_data_filtered = []
        for order, user in orders_data:
            # Buscar la factura asociada
            invoice = Invoice.query.filter(
                Invoice.customer_id == str(user.idUser)
            ).order_by(Invoice.invoice_date.desc()).first()
            
            payment_method = invoice.payment_method if invoice else 'Efectivo'
            
            # Aplicar filtro de método de pago
            if payment_filter != 'all' and payment_method != payment_filter:
                continue
            
            # Contar items del pedido
            items_count = OrderDetail.query.filter_by(idOrder=order.idOrder).count()
            
            order_data = {
                'id': order.idOrder,
                'user_id': user.idUser,
                'customer_name': user.nameUser,
                'total': float(order.totalAmount) if order.totalAmount else 0.0,
                'payment_method': payment_method,
                'status': order.status,
                'created_at': order.orderDate.isoformat() if order.orderDate else None,
                'items_count': items_count
            }
            
            orders_data_filtered.append(order_data)
        
        print(f"🎉 Se procesaron {len(orders_data_filtered)} pedidos exitosamente")
        return jsonify({'success': True, 'orders': orders_data_filtered})
    
    except Exception as e:
        print(f"❌ Error grave en get_orders: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error del servidor: {str(e)}'}), 500

@admin_bp.route('/mark_order_paid', methods=['POST'])
@login_required
def mark_order_paid():
    try:
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': 'No autorizado'})
        
        data = request.get_json()
        order_id = data.get('order_id')
        
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'success': False, 'message': 'Pedido no encontrado'})
        
        order.status = 'Completado'
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Pedido marcado como pagado'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/update_order_status', methods=['POST'])
@login_required
def update_order_status():
    """Endpoint para actualizar estado de pedido y enviar notificación"""
    try:
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': 'No autorizado'}), 403
        
        data = request.get_json()
        order_id = data.get('order_id')
        new_status = data.get('new_status')
        send_email = data.get('send_email', True)  # Por defecto enviar email
        
        if not order_id or not new_status:
            return jsonify({'success': False, 'message': 'Datos incompletos'}), 400
        
        # Buscar el pedido
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'success': False, 'message': 'Pedido no encontrado'}), 404
        
        # Guardar el estado anterior
        old_status = order.status
        order.status = new_status
        order.updated_at = datetime.utcnow()
        
        # Obtener información del cliente
        customer = User.query.get(order.idUser)
        
        db.session.commit()
        
        email_sent = False
        # Enviar notificación por correo si está habilitado
        if send_email and customer and customer.emailUser:
            # Crear detalles adicionales para el email
            order_details = f"Tu pedido ha cambiado de '{old_status}' a '{new_status}'"
            
            # Importar la función de envío de email
            from app.routes.auth import send_order_status_email
            
            email_sent = send_order_status_email(
                customer_email=customer.emailUser,
                customer_name=customer.nameUser,
                order_id=order_id,
                new_status=new_status,
                order_details=order_details
            )
        
        return jsonify({
            'success': True, 
            'message': f'Estado del pedido #{order_id} actualizado a {new_status}',
            'email_sent': email_sent
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Error actualizando estado del pedido: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Error del servidor: {str(e)}'
        }), 500

@admin_bp.route('/order/<int:order_id>')
@login_required
def order_details(order_id):
    if not current_user.is_admin:
        return "No autorizado", 403
    
    order = Order.query.get(order_id)
    if not order:
        return "Pedido no encontrado", 404
    
    user = User.query.get(order.idUser)
    order_details = OrderDetail.query.filter_by(idOrder=order_id).all()
    invoice = Invoice.query.filter_by(customer_id=str(user.idUser)).first()
    
    return render_template('admin_order_details.html', 
                         order=order, 
                         user=user, 
                         order_details=order_details,
                         invoice=invoice)

# ✅ RUTA PARA LA GESTIÓN DE PEDIDOS (HTML)
@admin_bp.route('/orders')
@login_required
def admin_orders():
    """Página de gestión de pedidos para administradores"""
    if not current_user.is_admin:
        return "No autorizado", 403
    return render_template('admin/orders.html')

# ✅ RUTA DE PRUEBA PARA DEBUG
@admin_bp.route('/test')
def test_route():
    return jsonify({
        'success': True, 
        'message': '✅ El blueprint admin está funcionando correctamente!',
        'routes_available': [
            '/admin/dashboard',
            '/admin/get_orders', 
            '/admin/mark_order_paid',
            '/admin/update_order_status',
            '/admin/order/<id>',
            '/admin/orders',
            '/admin/test'
        ]
    })

# FUNCIÓN PARA ENVIAR NOTIFICACIONES DE ESTADO DE PEDIDO
def send_order_status_email(customer_email, customer_name, order_id, new_status, order_details=None):
    try:
        # Mapeo de estados a mensajes más descriptivos
        status_messages = {
            'Pendiente': 'está pendiente de revisión',
            'Procesando': 'se está procesando y preparando',
            'Enviado': 'ha sido enviado',
            'Completado': 'ha sido completado y entregado',
            'Cancelado': 'ha sido cancelado'
        }
        
        status_icons = {
            'Pendiente': '⏳',
            'Procesando': '🔄',
            'Enviado': '🚚',
            'Completado': '✅',
            'Cancelado': '❌'
        }
        
        status_message = status_messages.get(new_status, f'tiene el estado: {new_status}')
        status_icon = status_icons.get(new_status, '📦')

        from flask_mail import Message
        
        msg = Message(
            subject=f'{status_icon} Actualización de tu Pedido #{order_id} - Fashion Boutique',
            sender=('Fashion Boutique', 'noreply.fashionboutique@gmail.com'),
            recipients=[customer_email]
        )

        # Crear el cuerpo HTML del email
        msg.html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Arial', sans-serif;
                    background-color: #f4f4f4;
                    margin: 0;
                    padding: 0;
                }}
                .email-container {{
                    max-width: 600px;
                    margin: 20px auto;
                    background: white;
                    border-radius: 10px;
                    overflow: hidden;
                    box-shadow: 0 0 20px rgba(0,0,0,0.1);
                }}
                .header {{
                    background: #000000;
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: bold;
                }}
                .content {{
                    padding: 30px;
                }}
                .status-update {{
                    background: #f8f9fa;
                    padding: 25px;
                    border-radius: 8px;
                    margin: 20px 0;
                    text-align: center;
                    border-left: 4px solid #4A90E2;
                }}
                .order-info {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                    border: 1px solid #e9ecef;
                }}
                .next-steps {{
                    background: #e8f5e8;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .tracking-info {{
                    background: #fff3cd;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .footer {{
                    background: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    color: #666;
                    font-size: 12px;
                }}
                .status-badge {{
                    display: inline-block;
                    padding: 8px 16px;
                    background: #4A90E2;
                    color: white;
                    border-radius: 20px;
                    font-weight: bold;
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="header">
                    <h1>FASHION BOUTIQUE</h1>
                    <p>Actualización de Pedido</p>
                </div>
                
                <div class="content">
                    <h2>¡Hola {customer_name}!</h2>
                    <p>Queremos informarte sobre el estado actual de tu pedido en <strong>Fashion Boutique</strong>.</p>
                    
                    <div class="status-update">
                        <h3>{status_icon} Estado Actualizado</h3>
                        <div class="status-badge">{new_status}</div>
                        <p>Tu pedido <strong>#{order_id}</strong> {status_message}.</p>
                    </div>
                    
                    <div class="order-info">
                        <h4>📋 Resumen del Pedido</h4>
                        <p><strong>Número de Pedido:</strong> #{order_id}</p>
                        <p><strong>Estado Actual:</strong> {new_status}</p>
                        <p><strong>Fecha de Actualización:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                        {f'<p><strong>Detalles:</strong> {order_details}</p>' if order_details else ''}
                    </div>
                    
                    {f'''
                    <div class="tracking-info">
                        <h4>📦 Información de Envío</h4>
                        <p>Tu pedido está en camino. Recibirás actualizaciones del envío próximamente.</p>
                        <p><strong>💡 Tip:</strong> Mantén tu teléfono disponible para coordinar la entrega.</p>
                    </div>
                    ''' if new_status == 'Enviado' else ''}
                    
                    {f'''
                    <div class="next-steps">
                        <h4>🎉 ¡Pedido Entregado!</h4>
                        <p>Tu pedido ha sido completado exitosamente. ¡Esperamos que disfrutes tus productos!</p>
                        <p><strong>¿Tienes alguna pregunta?</strong> No dudes en contactarnos.</p>
                    </div>
                    ''' if new_status == 'Completado' else ''}
                    
                    {f'''
                    <div class="next-steps" style="background: #ffe6e6;">
                        <h4>❌ Pedido Cancelado</h4>
                        <p>Lamentamos informarte que tu pedido ha sido cancelado.</p>
                        <p>Si crees que esto es un error o necesitas más información, por favor contáctanos inmediatamente.</p>
                    </div>
                    ''' if new_status == 'Cancelado' else ''}
                    
                    <p>Puedes ver el detalle completo de tu pedido en tu cuenta de Fashion Boutique.</p>
                    
                    <p>Si tienes alguna pregunta sobre tu pedido, estamos aquí para ayudarte.</p>
                </div>
                
                <div class="footer">
                    <p>© 2025 Fashion Boutique. Todos los derechos reservados.</p>
                    <p>Este es un email automático, por favor no responder.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Versión de texto plano
        msg.body = f"""
        ACTUALIZACIÓN DE PEDIDO #{order_id} - Fashion Boutique
        
        Hola {customer_name},
        
        El estado de tu pedido #{order_id} ha sido actualizado a: {new_status}
        
        {f'Detalles: {order_details}' if order_details else ''}
        
        Estado: {new_status}
        Fecha de actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}
        
        {f'📦 Tu pedido está en camino. Recibirás actualizaciones del envío próximamente.' if new_status == 'Enviado' else ''}
        {f'🎉 ¡Tu pedido ha sido completado exitosamente! Esperamos que disfrutes tus productos.' if new_status == 'Completado' else ''}
        {f'❌ Lamentamos informarte que tu pedido ha sido cancelado. Si necesitas más información, contáctanos.' if new_status == 'Cancelado' else ''}
        
        Si tienes preguntas, no dudes en contactarnos.
        
        Atentamente,
        El equipo de Fashion Boutique
        """

        mail.send(msg)
        logger.info(f"✅ Notificación de estado {new_status} enviada para pedido #{order_id} a {customer_email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enviando notificación de estado: {str(e)}")
        return False