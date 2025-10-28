from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from app import db, mail
from app.models1 import User, Invitation
from flask_mail import Message
from werkzeug.security import generate_password_hash, check_password_hash
import logging
import random
import string
from datetime import datetime, timedelta
import secrets

# Configurar logging
logger = logging.getLogger(__name__)

# Crear el Blueprint
bp = Blueprint('auth', __name__)

# FUNCIÓN PARA ENVIAR FACTURA POR EMAIL
def send_invoice_email(customer_email, customer_name, invoice_number, invoice_html, invoice_data):
    try:
        msg = Message(
            subject=f'🧾 Factura {invoice_number} - Fashion Boutique',
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
                    max-width: 800px;
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
                .invoice-preview {{
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .invoice-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                .invoice-table th,
                .invoice-table td {{
                    border: 1px solid #ddd;
                    padding: 12px;
                    text-align: left;
                }}
                .invoice-table th {{
                    background-color: #000;
                    color: white;
                }}
                .totals {{
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                    margin-top: 20px;
                }}
                .footer {{
                    background: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    color: #666;
                    font-size: 12px;
                }}
                .thank-you {{
                    text-align: center;
                    margin: 30px 0;
                    font-size: 18px;
                    color: #333;
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="header">
                    <h1>FASHION BOUTIQUE</h1>
                    <p>Factura Electrónica</p>
                </div>
                
                <div class="content">
                    <h2>¡Hola {customer_name}!</h2>
                    <p>Gracias por tu compra en <strong>Fashion Boutique</strong>. Adjuntamos tu factura para que la tengas disponible.</p>
                    
                    <div class="invoice-preview">
                        <h3>Factura #{invoice_number}</h3>
                        
                        <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
                            <div>
                                <strong>Fecha:</strong> {datetime.now().strftime('%d/%m/%Y')}<br>
                                <strong>Cliente:</strong> {customer_name}
                            </div>
                            <div style="text-align: right;">
                                <strong>Método de Pago:</strong> {invoice_data.get('payment_method', 'N/A')}<br>
                                {invoice_data.get('payment_details', '')}
                            </div>
                        </div>
                        
                        <table class="invoice-table">
                            <thead>
                                <tr>
                                    <th>Producto</th>
                                    <th>Precio Unit.</th>
                                    <th>Cantidad</th>
                                    <th>Descuento</th>
                                    <th>Subtotal</th>
                                </tr>
                            </thead>
                            <tbody>
                                {invoice_html}
                            </tbody>
                        </table>
                        
                        <div class="totals" style="text-align: right;">
                            <div style="margin-bottom: 10px;">
                                <strong>Subtotal:</strong> ${invoice_data.get('subtotal', 0):.2f}
                            </div>
                            <div style="margin-bottom: 10px;">
                                <strong>Descuento:</strong> ${invoice_data.get('total_discount', 0):.2f}
                            </div>
                            <div style="margin-bottom: 10px;">
                                <strong>Impuestos (21%):</strong> ${invoice_data.get('taxes', 0):.2f}
                            </div>
                            <div style="font-size: 18px; font-weight: bold;">
                                <strong>TOTAL:</strong> ${invoice_data.get('total', 0):.2f}
                            </div>
                        </div>
                    </div>
                    
                    <div class="thank-you">
                        <p>¡Gracias por confiar en Fashion Boutique! 🛍️</p>
                        <p>Esperamos verte pronto de nuevo.</p>
                    </div>
                    
                    <p>Si tienes alguna pregunta sobre tu factura, no dudes en contactarnos.</p>
                </div>
                
                <div class="footer">
                    <p>© 2025 Fashion Boutique. Todos los derechos reservados.</p>
                    <p>Este es un email automático, por favor no responder.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Versión de texto plano para clientes de email que no soportan HTML
        msg.body = f"""
        FACTURA {invoice_number} - Fashion Boutique
        
        ¡Hola {customer_name}!
        
        Gracias por tu compra en Fashion Boutique.
        
        Detalles de la factura:
        - Número: {invoice_number}
        - Fecha: {datetime.now().strftime('%d/%m/%Y')}
        - Cliente: {customer_name}
        - Método de Pago: {invoice_data.get('payment_method', 'N/A')}
        
        Productos:
        {chr(10).join([f"- {item.get('name', '')} | ${item.get('price', 0):.2f} x {item.get('quantity', 0)} = ${item.get('subtotal', 0):.2f}" for item in invoice_data.get('items', [])])}
        
        Resumen:
        - Subtotal: ${invoice_data.get('subtotal', 0):.2f}
        - Descuento: ${invoice_data.get('total_discount', 0):.2f}
        - Impuestos (21%): ${invoice_data.get('taxes', 0):.2f}
        - TOTAL: ${invoice_data.get('total', 0):.2f}
        
        ¡Gracias por tu compra!
        
        Fashion Boutique
        """

        mail.send(msg)
        logger.info(f"✅ Factura {invoice_number} enviada a {customer_email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enviando factura: {str(e)}")
        return False

# RUTA PARA ENVIAR FACTURAS
@bp.route('/send_invoice', methods=['POST'])
def send_invoice():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Datos no válidos'})
        
        # Obtener datos de la factura
        invoice_data = data
        
        # Obtener información del cliente
        customer_email = invoice_data.get('customer_email')
        customer_name = invoice_data.get('customer_name', 'Cliente')
        invoice_number = invoice_data.get('invoice_number', 'N/A')
        
        if not customer_email:
            return jsonify({'success': False, 'message': 'Email del cliente requerido'})
        
        # Crear el contenido HTML de los items de la factura
        items_html = ""
        for item in invoice_data.get('items', []):
            items_html += f"""
            <tr>
                <td>{item.get('name', '')}</td>
                <td>${item.get('price', 0):.2f}</td>
                <td>{item.get('quantity', 0)}</td>
                <td>{item.get('discount', 0)}%</td>
                <td>${item.get('subtotal', 0):.2f}</td>
            </tr>
            """
        
        # Enviar el email
        if send_invoice_email(customer_email, customer_name, invoice_number, items_html, invoice_data):
            return jsonify({
                'success': True, 
                'message': f'✅ Factura enviada exitosamente a {customer_email}'
            })
        else:
            return jsonify({
                'success': False, 
                'message': '❌ Error al enviar la factura por email'
            })
            
    except Exception as e:
        logger.error(f"❌ Error enviando factura: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'❌ Error del servidor: {str(e)}'
        })

# (MANTÉN TODAS LAS OTRAS FUNCIONES QUE YA TENÍAS)
# FUNCIÓN PARA ENVIAR EMAIL DE BIENVENIDA
def send_welcome_email(user):
    try:
        msg = Message(
            subject='🎉 ¡Bienvenido/a a Fashion Boutique!',
            sender=('Fashion Boutique', 'noreply.fashionboutique@gmail.com'),
            recipients=[user.emailUser]
        )

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
                .container {{
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
                .welcome-text {{
                    font-size: 18px;
                    color: #333;
                    line-height: 1.6;
                }}
                .features {{
                    margin: 20px 0;
                    padding: 15px;
                    background: #f8f9fa;
                    border-radius: 8px;
                }}
                .features li {{
                    margin: 10px 0;
                }}
                .cta-button {{
                    display: inline-block;
                    background: #4A90E2;
                    color: white;
                    padding: 12px 25px;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin: 20px 0;
                    transition: background-color 0.3s ease;
                }}
                .cta-button:hover {{
                    background: #357ABD;
                }}
                .footer {{
                    background: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>FASHION BOUTIQUE</h1>
                </div>
                
                <div class="content">
                    <h2>¡Hola {user.nameUser}!</h2>
                    
                    <div class="welcome-text">
                        <p>Nos alegra enormemente darte la bienvenida a <strong>Fashion Boutique</strong>.</p>
                        <p>Tu registro se ha completado exitosamente y ahora formas parte de nuestra comunidad de moda.</p>
                    </div>
                    
                    <div class="features">
                        <h3>✨ Lo que puedes disfrutar:</h3>
                        <ul>
                            <li>📦 Productos de moda exclusivos y tendencias actuales</li>
                            <li>🎁 Ofertas especiales y descuentos para miembros</li>
                            <li>🚚 Envíos rápidos y seguros</li>
                            <li>⭐ Atención personalizada 24/7</li>
                            <li>💝 Recomendaciones basadas en tu estilo</li>
                        </ul>
                    </div>
                    
                    <p>Estamos aquí para ayudarte a encontrar tu estilo único.</p>
                    
                    <center>
                        <a href="{url_for('auth.login', _external=True)}" class="cta-button">
                            Comenzar a comprar
                        </a>
                    </center>
                    
                    <p>Si tienes alguna pregunta, no dudes en contactarnos en cualquier momento.</p>
                    
                    <p>¡Bienvenido/a a la familia Fashion Boutique! 🛍️</p>
                </div>
                
                <div class="footer">
                    <p>© 2025 Fashion Boutique. Todos los derechos reservados.</p>
                    <p>Este es un email automático, por favor no responder.</p>
                </div>
            </div>
        </body>
        </html>
        """

        msg.body = f"""
        FASHION BOUTIQUE - ¡Bienvenido/a!
        
        Hola {user.nameUser},
        
        ¡Bienvenido/a a Fashion Boutique!
        
        Tu registro se ha completado exitosamente. Ahora puedes:
        - Explorar nuestra colección exclusiva
        - Disfrutar de ofertas especiales
        - Recibir envíos rápidos y seguros
        - Obtener atención personalizada
        
        Inicia sesión aquí: {url_for('auth.login', _external=True)}
        
        Si tienes preguntas, estamos aquí para ayudarte.
        
        ¡Gracias por unirte a nosotros!
        
        Atentamente,
        El equipo de Fashion Boutique
        """

        mail.send(msg)
        logger.info(f"✅ Email de bienvenida enviado a {user.emailUser}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enviando email de bienvenida: {str(e)}")
        return False

# FUNCIÓN PARA ENVIAR EMAIL DE VERIFICACIÓN
def send_verification_email(user, verification_code):
    try:
        msg = Message(
            subject='🔐 Código de Verificación - Fashion Boutique',
            sender=('Fashion Boutique', 'noreply.fashionboutique@gmail.com'),
            recipients=[user.emailUser]
        )

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
                .container {{
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
                .code-container {{
                    text-align: center;
                    margin: 30px 0;
                }}
                .verification-code {{
                    display: inline-block;
                    background: #4A90E2;
                    color: white;
                    font-size: 32px;
                    font-weight: bold;
                    padding: 15px 30px;
                    border-radius: 8px;
                    letter-spacing: 5px;
                }}
                .warning {{
                    background: #fff3cd;
                    border: 1px solid #ffeaa7;
                    border-radius: 5px;
                    padding: 15px;
                    margin: 20px 0;
                }}
                .footer {{
                    background: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>FASHION BOUTIQUE</h1>
                </div>
                
                <div class="content">
                    <h2>Hola {user.nameUser},</h2>
                    <p>Has solicitado restablecer tu contraseña en <strong>Fashion Boutique</strong>. 
                       Usa el siguiente código de verificación para continuar:</p>
                    
                    <div class="code-container">
                        <div class="verification-code">{verification_code}</div>
                    </div>
                    
                    <div class="warning">
                        <strong>⚠️ Importante de seguridad:</strong>
                        <ul>
                            <li>Este código expirará en <strong>10 minutos</strong></li>
                            <li>No compartas este código con nadie</li>
                            <li>Si no solicitaste este cambio, ignora este email</li>
                        </ul>
                    </div>
                    
                    <p>Ingresa este código en la página de verificación para completar el proceso.</p>
                </div>
                
                <div class="footer">
                    <p>© 2025 Fashion Boutique. Todos los derechos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """

        msg.body = f"""
        FASHION BOUTIQUE - Código de Verificación
        
        Hola {user.nameUser},
        
        Tu código de verificación es: {verification_code}
        
        Este código expirará en 10 minutos.
        
        Atentamente,
        El equipo de Fashion Boutique
        """

        mail.send(msg)
        logger.info(f"✅ Email de verificación enviado a {user.emailUser}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enviando email: {str(e)}")
        return False

# FUNCIÓN PARA ENVIAR EMAIL DE INVITACIÓN
def send_invitation_email(email, role, custom_message, registration_link):
    try:
        msg = Message(
            subject='🎉 Invitación para unirte a Fashion Boutique',
            sender=('Fashion Boutique', 'noreply.fashionboutique@gmail.com'),
            recipients=[email]
        )

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
                .container {{
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
                .welcome-text {{
                    font-size: 18px;
                    color: #333;
                    line-height: 1.6;
                }}
                .invitation-details {{
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .cta-button {{
                    display: inline-block;
                    background: #4A90E2;
                    color: white;
                    padding: 14px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin: 20px 0;
                    transition: background-color 0.3s ease;
                }}
                .cta-button:hover {{
                    background: #357ABD;
                }}
                .footer {{
                    background: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>FASHION BOUTIQUE</h1>
                    <p>Invitación Exclusiva</p>
                </div>
                
                <div class="content">
                    <h2>¡Te estamos esperando!</h2>
                    
                    <div class="invitation-details">
                        <p><strong>Has sido invitado/a como:</strong> {role}</p>
                        {f'<p><strong>Mensaje personal:</strong> "{custom_message}"</p>' if custom_message else ''}
                    </div>
                    
                    <div class="welcome-text">
                        <p>Nos complace invitarte a unirte a <strong>Fashion Boutique</strong>, tu destino de moda exclusivo.</p>
                        <p>Como miembro de nuestra comunidad, podrás disfrutar de:</p>
                        <ul>
                            <li>🎁 Productos de moda exclusivos</li>
                            <li>🚚 Envíos rápidos y seguros</li>
                            <li>⭐ Ofertas especiales para miembros</li>
                            <li>💝 Atención personalizada</li>
                        </ul>
                    </div>
                    
                    <center>
                        <a href="{registration_link}" class="cta-button">
                            Completar Mi Registro
                        </a>
                    </center>
                    
                    <p><strong>⚠️ Importante:</strong> Este enlace expirará en 7 días.</p>
                    
                    <p>Si tienes alguna pregunta, no dudes en contactarnos.</p>
                    
                    <p>¡Esperamos verte pronto en Fashion Boutique! 🛍️</p>
                </div>
                
                <div class="footer">
                    <p>© 2025 Fashion Boutique. Todos los derechos reservados.</p>
                    <p>Este es un email automático, por favor no responder.</p>
                </div>
            </div>
        </body>
        </html>
        """

        msg.body = f"""
        FASHION BOUTIQUE - Invitación Exclusiva
        
        ¡Te estamos esperando!
        
        Has sido invitado/a a unirte a Fashion Boutique como: {role}
        
        {f'Mensaje personal: "{custom_message}"' if custom_message else ''}
        
        Como miembro de nuestra comunidad, podrás disfrutar de:
        - Productos de moda exclusivos
        - Envíos rápidos y seguros
        - Ofertas especiales para miembros
        - Atención personalizada
        
        Completa tu registro aquí: {registration_link}
        
        ⚠️ Importante: Este enlace expirará en 7 días.
        
        Si tienes alguna pregunta, no dudes en contactarnos.
        
        ¡Esperamos verte pronto en Fashion Boutique!
        
        Atentamente,
        El equipo de Fashion Boutique
        """

        mail.send(msg)
        logger.info(f"✅ Email de invitación enviado a {email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enviando email de invitación: {str(e)}")
        return False

# GENERAR CÓDIGO DE VERIFICACIÓN
def generate_verification_code():
    return ''.join(random.choices(string.digits, k=6))

# RUTAS DE AUTENTICACIÓN
@bp.route('/')
def home():
    """Página principal - Redirige al login"""
    return redirect(url_for('auth.login'))

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('users.admin_dashboard'))
        else:
            return redirect(url_for('users.profile'))
    
    if request.method == 'POST':
        nameUser = request.form.get('nameUser')
        passwordUser = request.form.get('passwordUser')
        
        user = User.query.filter_by(nameUser=nameUser).first()
        
        if user and user.check_password(passwordUser):
            login_user(user)
            flash('¡Inicio de sesión exitoso!', 'success')
            
            if user.is_admin:
                return redirect(url_for('users.admin_dashboard'))
            else:
                return redirect(url_for('users.profile'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
    
    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('users.admin_dashboard'))
        else:
            return redirect(url_for('users.profile'))
    
    # Obtener parámetros de invitación para GET requests
    invited_email = request.args.get('invited_email') or request.args.get('email')
    invited_role = request.args.get('invited_role') or request.args.get('role')
    invitation_token = request.args.get('token')
    
    if request.method == 'POST':
        nameUser = request.form.get('nameUser')
        emailUser = request.form.get('emailUser')
        passwordUser = request.form.get('passwordUser')
        confirmPassword = request.form.get('confirmPassword')
        invitation_token = request.form.get('invitation_token')
        
        if passwordUser != confirmPassword:
            flash('Las contraseñas no coinciden', 'danger')
            return render_template('register.html',
                                invited_email=invited_email,
                                invited_role=invited_role,
                                invitation_token=invitation_token)
        
        if User.query.filter_by(emailUser=emailUser).first():
            flash('El email ya está registrado', 'danger')
            return render_template('register.html',
                                invited_email=invited_email,
                                invited_role=invited_role,
                                invitation_token=invitation_token)
        
        if User.query.filter_by(nameUser=nameUser).first():
            flash('El nombre de usuario ya existe', 'danger')
            return render_template('register.html',
                                invited_email=invited_email,
                                invited_role=invited_role,
                                invitation_token=invitation_token)
        
        try:
            # Determinar si es admin basado en la invitación
            is_admin = (invited_role == 'Administrador') if invited_role else False
            
            new_user = User(
                nameUser=nameUser,
                emailUser=emailUser,
                is_admin=is_admin
            )
            new_user.set_password(passwordUser)
            
            db.session.add(new_user)
            
            # Si viene de una invitación, marcarla como usada
            if invitation_token:
                invitation = Invitation.query.filter_by(token=invitation_token).first()
                if invitation:
                    invitation.used = True
                    flash(f'¡Bienvenido/a {nameUser}! Tu cuenta de {invited_role} ha sido activada.', 'success')
                else:
                    flash(f'¡Bienvenido/a {nameUser}! Tu cuenta ha sido creada exitosamente.', 'success')
            else:
                flash(f'¡Bienvenido/a {nameUser}! Tu cuenta ha sido creada exitosamente.', 'success')
            
            db.session.commit()
            
            # Enviar email de bienvenida
            if send_welcome_email(new_user):
                logger.info(f"Email de bienvenida enviado a {new_user.emailUser}")
            else:
                logger.warning(f"No se pudo enviar email de bienvenida a {new_user.emailUser}")
            
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la cuenta: {str(e)}', 'danger')
    
    return render_template('register.html',
                         invited_email=invited_email,
                         invited_role=invited_role,
                         invitation_token=invitation_token)

@bp.route('/register/<token>')
def register_with_token(token):
    # Verificar si la invitación es válida
    invitation = Invitation.query.filter_by(
        token=token, 
        used=False
    ).filter(Invitation.expires_at > datetime.utcnow()).first()
    
    if not invitation:
        flash('Enlace de invitación inválido o expirado', 'danger')
        return redirect(url_for('auth.register'))
    
    # Pasar el email y rol al template de registro
    return render_template(
        'register.html',
        invited_email=invitation.email,
        invited_role=invitation.role,
        invitation_token=token
    )

@bp.route('/send_invitation', methods=['POST'])
def send_invitation():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Datos no válidos'})
            
        email = data.get('email')
        role = data.get('role', 'Cliente')
        custom_message = data.get('message', '')
        
        # Validaciones
        if not email:
            return jsonify({'success': False, 'message': 'El email es requerido'})
        
        # Verificar si el email ya está registrado
        existing_user = User.query.filter_by(emailUser=email).first()
        if existing_user:
            return jsonify({'success': False, 'message': 'Este email ya está registrado en el sistema'})
        
        # Verificar si ya hay una invitación pendiente
        existing_invitation = Invitation.query.filter_by(
            email=email, 
            used=False
        ).filter(Invitation.expires_at > datetime.utcnow()).first()
        
        if existing_invitation:
            return jsonify({'success': False, 'message': 'Ya hay una invitación pendiente para este email'})
        
        # Generar token único
        token = secrets.token_urlsafe(32)
        expiration = datetime.utcnow() + timedelta(days=7)
        
        # Guardar invitación en la base de datos
        invitation = Invitation(
            email=email,
            role=role,
            token=token,
            expires_at=expiration
        )
        
        db.session.add(invitation)
        db.session.commit()
        
        # Crear enlace de registro
        registration_link = url_for('auth.register_with_token', token=token, _external=True)
        
        # Enviar correo
        if send_invitation_email(email, role, custom_message, registration_link):
            return jsonify({
                'success': True, 
                'message': f'✅ Invitación enviada exitosamente a {email}'
            })
        else:
            # Si falla el email, eliminar la invitación
            db.session.delete(invitation)
            db.session.commit()
            return jsonify({
                'success': False, 
                'message': '❌ Error al enviar el correo de invitación'
            })
        
    except Exception as e:
        logger.error(f"❌ Error en send_invitation: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'❌ Error del servidor: {str(e)}'
        })

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente', 'info')
    return redirect('/')

@bp.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(emailUser=email).first()
        
        if user:
            try:
                verification_code = generate_verification_code()
                user.verification_code = verification_code
                user.verification_code_expiration = datetime.utcnow() + timedelta(minutes=10)
                
                db.session.commit()
                
                if send_verification_email(user, verification_code):
                    session['reset_email'] = email
                    flash('Código de verificación enviado a tu email', 'success')
                    return redirect(url_for('auth.verify_reset_code'))
                else:
                    flash('Error al enviar el email', 'danger')
                    
            except Exception as e:
                db.session.rollback()
                flash('Error al procesar la solicitud', 'danger')
        else:
            flash('Si el email existe, recibirás un código de verificación', 'info')
    
    return render_template('reset_request.html')

@bp.route('/verify_reset_code', methods=['GET', 'POST'])
def verify_reset_code():
    email = session.get('reset_email')
    if not email:
        return redirect(url_for('auth.reset_request'))
    
    user = User.query.filter_by(emailUser=email).first()
    if not user:
        flash('Solicitud inválida', 'danger')
        return redirect(url_for('auth.reset_request'))
    
    if request.method == 'POST':
        code = request.form.get('verification_code')
        
        if user.verification_code == code and user.verification_code_expiration > datetime.utcnow():
            session['verified_email'] = email
            flash('Código verificado correctamente', 'success')
            return redirect(url_for('auth.reset_token'))
        else:
            flash('Código inválido o expirado', 'danger')
    
    return render_template('verify_code.html', email=email)

@bp.route('/reset_token', methods=['GET', 'POST'])
def reset_token():
    email = session.get('verified_email')
    if not email:
        return redirect(url_for('auth.reset_request'))
    
    user = User.query.filter_by(emailUser=email).first()
    if not user:
        flash('Solicitud inválida', 'danger')
        return redirect(url_for('auth.reset_request'))
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('Las contraseñas no coinciden', 'danger')
        else:
            user.set_password(new_password)
            user.verification_code = None
            user.verification_code_expiration = None
            
            db.session.commit()
            
            session.pop('reset_email', None)
            session.pop('verified_email', None)
            
            flash('Contraseña restablecida correctamente', 'success')
            return redirect(url_for('auth.login'))
    
    return render_template('reset_token.html')

@bp.route('/test')
def test():
    return "✅ ¡La aplicación funciona correctamente!"



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