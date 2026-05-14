import os
import json
import re
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN", "8414661576:AAFvqJXHxpHAYGuuuQ7hcXPSGRJmaUci_40")

# Archivo de datos (en Railway persiste mientras el servicio corre)
DATA_FILE = "gastos.json"

# Categorías y palabras clave
CATEGORIAS = {
    "🍔 Comida": ["almuerzo", "lunch", "cafe", "café", "coffee", "kiosco", "delivery", "medialunas", "empanada", "pizza", "sandwich", "comida", "facturas", "desayuno", "merienda", "tostado", "milanesa"],
    "🍽️ Salidas": ["cena", "restaurant", "restaurante", "after", "amigos", "parrilla", "sushi", "birra", "cerveza", "chopps", "chopp", "cumple", "cumpleaños"],
    "💃 Salidas nocturnas": ["boliche", "tragos", "trago", "chicas", "club", "disco", "gin", "fernet", "copas", "noche", "salida"],
    "👗 Ropa": ["ropa", "zapatillas", "remera", "pantalon", "pantalón", "camisa", "calzado", "jean", "buzo", "campera", "remerita"],
    "⚽ Fútbol": ["futbol", "fútbol", "cancha", "pelota", "indumentaria", "camiseta", "botines", "arco", "deporte"],
    "🚗 Transporte": ["nafta", "uber", "taxi", "peaje", "combustible", "remis", "colectivo", "subte", "tren", "auto", "estacionamiento"],
    "📱 Servicios": ["netflix", "spotify", "internet", "celular", "suscripcion", "suscripción", "disney", "hbo", "prime", "youtube"],
    "💳 Deudas": ["cuota", "tarjeta", "prestamo", "préstamo", "deuda", "credito", "crédito", "banco", "pago"],
    "🏠 Casa": ["supermercado", "limpieza", "mantenimiento", "alquiler", "expensas", "luz", "gas", "agua", "mercado"],
    "🎯 Otros": []
}

def cargar_datos():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def guardar_datos(datos):
    with open(DATA_FILE, "w") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

def categorizar(concepto):
    concepto_lower = concepto.lower()
    for cat, palabras in CATEGORIAS.items():
        for p in palabras:
            if p in concepto_lower:
                return cat
    return "🎯 Otros"

def parsear_gasto(texto):
    """Parsea mensajes como 'café 800' o '1500 almuerzo' o 'nafta $2000'"""
    texto = texto.strip().replace("$", "").replace(",", "")
    # Patrón: concepto + número o número + concepto
    patron1 = re.match(r'^(.+?)\s+(\d+(?:\.\d+)?)$', texto)
    patron2 = re.match(r'^(\d+(?:\.\d+)?)\s+(.+)$', texto)
    
    if patron1:
        concepto = patron1.group(1).strip()
        monto = float(patron1.group(2))
        return concepto, monto
    elif patron2:
        monto = float(patron2.group(1))
        concepto = patron2.group(2).strip()
        return concepto, monto
    return None, None

def fmt_monto(n):
    return f"${int(n):,}".replace(",", ".")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    nombre = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 Hola {nombre}!\n\n"
        f"Soy tu bot de gastos personales. Mandame tus gastos así:\n\n"
        f"  *café 800*\n"
        f"  *almuerzo 1500*\n"
        f"  *nafta 8000*\n"
        f"  *salida chicas 15000*\n\n"
        f"📊 Comandos disponibles:\n"
        f"  /resumen — ver gastos del mes\n"
        f"  /hoy — gastos de hoy\n"
        f"  /categorias — ver por categoría\n"
        f"  /consejos — análisis y consejos de ahorro\n"
        f"  /borrar_ultimo — borrar el último gasto\n",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    texto = update.message.text.strip()
    
    concepto, monto = parsear_gasto(texto)
    
    if not concepto or not monto:
        await update.message.reply_text(
            "No entendí. Mandame el gasto así:\n"
            "*concepto monto* — ej: *café 800*\n"
            "O usá /resumen para ver tus gastos",
            parse_mode="Markdown"
        )
        return
    
    categoria = categorizar(concepto)
    datos = cargar_datos()
    
    if user_id not in datos:
        datos[user_id] = []
    
    gasto = {
        "concepto": concepto,
        "monto": monto,
        "categoria": categoria,
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "hora": datetime.now().strftime("%H:%M")
    }
    datos[user_id].append(gasto)
    guardar_datos(datos)
    
    await update.message.reply_text(
        f"✓ *{concepto.capitalize()}* — {fmt_monto(monto)}\n"
        f"📁 {categoria}",
        parse_mode="Markdown"
    )

async def resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    datos = cargar_datos()
    gastos = datos.get(user_id, [])
    
    mes_actual = datetime.now().strftime("%Y-%m")
    gastos_mes = [g for g in gastos if g["fecha"].startswith(mes_actual)]
    
    if not gastos_mes:
        await update.message.reply_text("No tenés gastos registrados este mes. Empezá mandando un gasto!")
        return
    
    total = sum(g["monto"] for g in gastos_mes)
    
    # Agrupar por categoría
    por_cat = {}
    for g in gastos_mes:
        cat = g["categoria"]
        por_cat[cat] = por_cat.get(cat, 0) + g["monto"]
    
    # Ordenar por monto
    por_cat_sorted = sorted(por_cat.items(), key=lambda x: x[1], reverse=True)
    
    mes_nombre = datetime.now().strftime("%B %Y").upper()
    msg = f"📊 *RESUMEN {mes_nombre}*\n"
    msg += f"{'─'*28}\n"
    
    for cat, monto in por_cat_sorted:
        pct = int(monto/total*100)
        barra = "█" * (pct//10) + "░" * (10-pct//10)
        msg += f"{cat}\n{barra} {fmt_monto(monto)} ({pct}%)\n\n"
    
    msg += f"{'─'*28}\n"
    msg += f"💰 *TOTAL: {fmt_monto(total)}*\n"
    msg += f"📅 {len(gastos_mes)} gastos este mes"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    datos = cargar_datos()
    gastos = datos.get(user_id, [])
    
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    gastos_hoy = [g for g in gastos if g["fecha"] == hoy_str]
    
    if not gastos_hoy:
        await update.message.reply_text("No registraste gastos hoy todavía 👍")
        return
    
    total = sum(g["monto"] for g in gastos_hoy)
    msg = f"📅 *HOY — {datetime.now().strftime('%d/%m/%Y')}*\n{'─'*24}\n"
    
    for g in gastos_hoy:
        msg += f"• {g['concepto'].capitalize()} — {fmt_monto(g['monto'])} {g['categoria']}\n"
    
    msg += f"{'─'*24}\n*Total hoy: {fmt_monto(total)}*"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def categorias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    datos = cargar_datos()
    gastos = datos.get(user_id, [])
    mes_actual = datetime.now().strftime("%Y-%m")
    gastos_mes = [g for g in gastos if g["fecha"].startswith(mes_actual)]
    
    if not gastos_mes:
        await update.message.reply_text("Sin gastos este mes todavía.")
        return
    
    por_cat = {}
    for g in gastos_mes:
        cat = g["categoria"]
        if cat not in por_cat:
            por_cat[cat] = {"total": 0, "items": []}
        por_cat[cat]["total"] += g["monto"]
        por_cat[cat]["items"].append(f"  · {g['concepto'].capitalize()} {fmt_monto(g['monto'])}")
    
    msg = "📁 *GASTOS POR CATEGORÍA*\n\n"
    for cat, info in sorted(por_cat.items(), key=lambda x: x[1]["total"], reverse=True):
        msg += f"*{cat}* — {fmt_monto(info['total'])}\n"
        msg += "\n".join(info["items"][:5])
        if len(info["items"]) > 5:
            msg += f"\n  · ...y {len(info['items'])-5} más"
        msg += "\n\n"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def consejos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    datos = cargar_datos()
    gastos = datos.get(user_id, [])
    mes_actual = datetime.now().strftime("%Y-%m")
    gastos_mes = [g for g in gastos if g["fecha"].startswith(mes_actual)]
    
    if not gastos_mes:
        await update.message.reply_text("Registrá algunos gastos primero para darte consejos personalizados.")
        return
    
    total = sum(g["monto"] for g in gastos_mes)
    por_cat = {}
    for g in gastos_mes:
        por_cat[g["categoria"]] = por_cat.get(g["categoria"], 0) + g["monto"]
    
    top_cat = sorted(por_cat.items(), key=lambda x: x[1], reverse=True)[:3]
    
    msg = f"💡 *ANÁLISIS FINANCIERO PERSONAL*\n{'─'*28}\n\n"
    msg += f"💰 Gastaste *{fmt_monto(total)}* este mes\n\n"
    msg += f"🔴 *Top 3 categorías donde más gastás:*\n"
    
    for cat, monto in top_cat:
        pct = int(monto/total*100)
        msg += f"  {cat}: {fmt_monto(monto)} ({pct}%)\n"
    
    msg += f"\n💡 *Consejos para ahorrar:*\n"
    
    # Consejos personalizados según categorías
    for cat, monto in top_cat:
        if "Salidas nocturnas" in cat and monto > 20000:
            msg += f"\n🌙 En salidas nocturnas gastás {fmt_monto(monto)}. Intentá salir una vez menos por semana y podrías ahorrar {fmt_monto(monto*0.3)}/mes.\n"
        elif "Comida" in cat and monto > 30000:
            msg += f"\n🍔 En comida gastás {fmt_monto(monto)}. Cocinar en casa 3 veces por semana te puede ahorrar hasta {fmt_monto(monto*0.4)}/mes.\n"
        elif "Salidas" in cat and monto > 25000:
            msg += f"\n🍽️ En salidas gastás {fmt_monto(monto)}. Invitar amigos a casa en vez de ir a restaurantes puede bajar esto a la mitad.\n"
        elif "Deudas" in cat:
            msg += f"\n💳 Tenés {fmt_monto(monto)} en deudas/cuotas. Prioridad: saldar la deuda con mayor tasa primero.\n"
        elif "Servicios" in cat:
            msg += f"\n📱 Gastás {fmt_monto(monto)} en suscripciones. Revisá cuáles realmente usás — podés ahorrar fácil {fmt_monto(monto*0.3)}.\n"
    
    # Potencial de ahorro
    ahorro_posible = total * 0.20
    msg += f"\n\n✅ *Potencial de ahorro mensual: {fmt_monto(ahorro_posible)}*\n"
    msg += f"Si ahorrás esto 12 meses = *{fmt_monto(ahorro_posible*12)}/año*"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def borrar_ultimo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    datos = cargar_datos()
    gastos = datos.get(user_id, [])
    
    if not gastos:
        await update.message.reply_text("No tenés gastos registrados.")
        return
    
    ultimo = gastos.pop()
    datos[user_id] = gastos
    guardar_datos(datos)
    
    await update.message.reply_text(
        f"🗑️ Borrado: *{ultimo['concepto'].capitalize()}* — {fmt_monto(ultimo['monto'])}",
        parse_mode="Markdown"
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("resumen", resumen))
    app.add_handler(CommandHandler("hoy", hoy))
    app.add_handler(CommandHandler("categorias", categorias))
    app.add_handler(CommandHandler("consejos", consejos))
    app.add_handler(CommandHandler("borrar_ultimo", borrar_ultimo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()
