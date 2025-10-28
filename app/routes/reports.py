from flask import Blueprint, request, jsonify, send_file
from models import db, Invoice, InvoiceItem, Product, User, Order, OrderDetail
from datetime import datetime, timedelta
import json
import io
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import pythoncom

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/api/reports/generate', methods=['POST'])
def generate_report():
    try:
        data = request.get_json()
        report_type = data.get('report_type')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # Convertir fechas
        start_date = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
        end_date = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None
        
        results = {}
        
        if report_type == 'ventas':
            results = generate_sales_report(start_date, end_date)
        elif report_type == 'productos':
            results = generate_products_report(start_date, end_date)
        elif report_type == 'clientes':
            results = generate_customers_report(start_date, end_date)
        elif report_type == 'inventario':
            results = generate_inventory_report()
        
        return jsonify({
            'success': True,
            'data': results,
            'total_records': len(results.get('data', []))
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def generate_sales_report(start_date, end_date):
    """Generar reporte de ventas"""
    query = Invoice.query
    
    if start_date:
        query = query.filter(Invoice.invoice_date >= start_date)
    if end_date:
        # Añadir un día para incluir todo el día final
        end_date_with_time = end_date + timedelta(days=1)
        query = query.filter(Invoice.invoice_date < end_date_with_time)
    
    invoices = query.order_by(Invoice.invoice_date.desc()).all()
    
    data = []
    total_ventas = 0
    total_facturas = len(invoices)
    
    for invoice in invoices:
        data.append({
            'numero_factura': invoice.invoice_number,
            'fecha': invoice.invoice_date.strftime('%Y-%m-%d %H:%M'),
            'cliente': invoice.customer_name,
            'metodo_pago': invoice.payment_method,
            'subtotal': float(invoice.subtotal),
            'impuestos': float(invoice.taxes),
            'descuentos': float(invoice.total_discount),
            'total': float(invoice.total_amount),
            'estado': invoice.status
        })
        total_ventas += float(invoice.total_amount)
    
    return {
        'data': data,
        'summary': {
            'total_ventas': total_ventas,
            'total_facturas': total_facturas,
            'promedio_venta': total_ventas / total_facturas if total_facturas > 0 else 0
        }
    }

def generate_products_report(start_date, end_date):
    """Generar reporte de productos más vendidos"""
    # Consulta para productos vendidos
    query = db.session.query(
        Product.nameProduct,
        Product.idProduct,
        db.func.sum(InvoiceItem.quantity).label('total_vendido'),
        db.func.sum(InvoiceItem.subtotal).label('total_ingresos')
    ).join(InvoiceItem, Product.idProduct == InvoiceItem.idProduct)\
     .join(Invoice, InvoiceItem.idInvoice == Invoice.idInvoice)
    
    if start_date:
        query = query.filter(Invoice.invoice_date >= start_date)
    if end_date:
        end_date_with_time = end_date + timedelta(days=1)
        query = query.filter(Invoice.invoice_date < end_date_with_time)
    
    products_data = query.group_by(Product.idProduct, Product.nameProduct)\
                       .order_by(db.func.sum(InvoiceItem.subtotal).desc())\
                       .all()
    
    data = []
    for product in products_data:
        data.append({
            'producto': product.nameProduct,
            'id_producto': product.idProduct,
            'unidades_vendidas': int(product.total_vendido) if product.total_vendido else 0,
            'total_ingresos': float(product.total_ingresos) if product.total_ingresos else 0
        })
    
    return {
        'data': data,
        'summary': {
            'total_productos': len(data),
            'total_unidades_vendidas': sum(item['unidades_vendidas'] for item in data),
            'ingresos_totales': sum(item['total_ingresos'] for item in data)
        }
    }

def generate_customers_report(start_date, end_date):
    """Generar reporte de clientes"""
    query = db.session.query(
        Invoice.customer_name,
        Invoice.customer_email,
        Invoice.customer_id,
        db.func.count(Invoice.idInvoice).label('total_compras'),
        db.func.sum(Invoice.total_amount).label('total_gastado')
    )
    
    if start_date:
        query = query.filter(Invoice.invoice_date >= start_date)
    if end_date:
        end_date_with_time = end_date + timedelta(days=1)
        query = query.filter(Invoice.invoice_date < end_date_with_time)
    
    customers_data = query.group_by(
        Invoice.customer_name, 
        Invoice.customer_email, 
        Invoice.customer_id
    ).order_by(db.func.sum(Invoice.total_amount).desc()).all()
    
    data = []
    for customer in customers_data:
        data.append({
            'cliente': customer.customer_name,
            'email': customer.customer_email or 'No especificado',
            'identificacion': customer.customer_id or 'No especificado',
            'total_compras': customer.total_compras,
            'total_gastado': float(customer.total_gastado) if customer.total_gastado else 0
        })
    
    return {
        'data': data,
        'summary': {
            'total_clientes': len(data),
            'compras_totales': sum(item['total_compras'] for item in data),
            'ingresos_clientes': sum(item['total_gastado'] for item in data)
        }
    }

def generate_inventory_report():
    """Generar reporte de inventario"""
    products = Product.query.filter_by(status='Activo').order_by(Product.stock.asc()).all()
    
    data = []
    for product in products:
        # Calcular estado del inventario
        if product.stock == 0:
            estado = 'Agotado'
        elif product.stock <= 5:
            estado = 'Bajo Stock'
        else:
            estado = 'Disponible'
        
        data.append({
            'producto': product.nameProduct,
            'id_producto': product.idProduct,
            'categoria': product.category or 'Sin categoría',
            'precio': float(product.price),
            'stock_actual': product.stock,
            'estado_inventario': estado,
            'valor_total': float(product.price) * product.stock
        })
    
    return {
        'data': data,
        'summary': {
            'total_productos': len(data),
            'productos_agotados': sum(1 for item in data if item['estado_inventario'] == 'Agotado'),
            'productos_bajo_stock': sum(1 for item in data if item['estado_inventario'] == 'Bajo Stock'),
            'valor_inventario_total': sum(item['valor_total'] for item in data)
        }
    }

@reports_bp.route('/api/reports/export/excel', methods=['POST'])
def export_excel():
    try:
        data = request.get_json()
        report_data = data.get('data', [])
        report_type = data.get('report_type')
        start_date = data.get('start_date', '')
        end_date = data.get('end_date', '')
        
        # Crear DataFrame
        df = pd.DataFrame(report_data)
        
        # Crear output en memoria
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Reporte', index=False)
            
            # Autoajustar columnas
            worksheet = writer.sheets['Reporte']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        filename = f"reporte_{report_type}_{start_date}_to_{end_date}.xlsx"
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/api/reports/export/pdf', methods=['POST'])
def export_pdf():
    try:
        data = request.get_json()
        report_data = data.get('data', [])
        report_type = data.get('report_type')
        start_date = data.get('start_date', '')
        end_date = data.get('end_date', '')
        
        # Crear PDF en memoria
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        
        # Título
        title = Paragraph(f"Reporte de {report_type.capitalize()}", styles['Title'])
        elements.append(title)
        
        # Rango de fechas
        if start_date and end_date:
            date_range = Paragraph(f"Período: {start_date} a {end_date}", styles['Normal'])
            elements.append(date_range)
        
        elements.append(Spacer(1, 12))
        
        # Preparar datos para la tabla
        if report_data:
            # Encabezados
            headers = list(report_data[0].keys())
            data_table = [headers]
            
            # Datos
            for row in report_data:
                data_table.append([str(row.get(header, '')) for header in headers])
            
            # Crear tabla
            table = Table(data_table)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(table)
        
        # Generar PDF
        doc.build(elements)
        buffer.seek(0)
        
        filename = f"reporte_{report_type}_{start_date}_to_{end_date}.pdf"
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/api/reports/export/word', methods=['POST'])
def export_word():
    try:
        data = request.get_json()
        report_data = data.get('data', [])
        report_type = data.get('report_type')
        start_date = data.get('start_date', '')
        end_date = data.get('end_date', '')
        
        # Crear contenido HTML simple para Word
        html_content = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Reporte de {report_type}</title>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
            </style>
        </head>
        <body>
            <h1>Reporte de {report_type.capitalize()}</h1>
            <p>Período: {start_date} a {end_date}</p>
        """
        
        if report_data:
            html_content += "<table>"
            # Encabezados
            headers = list(report_data[0].keys())
            html_content += "<tr>"
            for header in headers:
                html_content += f"<th>{header}</th>"
            html_content += "</tr>"
            
            # Datos
            for row in report_data:
                html_content += "<tr>"
                for header in headers:
                    html_content += f"<td>{row.get(header, '')}</td>"
                html_content += "</tr>"
            
            html_content += "</table>"
        
        html_content += "</body></html>"
        
        # Crear archivo en memoria
        output = io.BytesIO()
        output.write(html_content.encode('utf-8'))
        output.seek(0)
        
        filename = f"reporte_{report_type}_{start_date}_to_{end_date}.doc"
        return send_file(
            output,
            mimetype='application/msword',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500