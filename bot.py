import os
import re
from datetime import datetime
from supabase import create_client, Client
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN", "8414661576:AAFvqJXHxpHAYGuuuQ7hcXPSGRJmaUci_40")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://lxemytiuojxexziecnbe.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_e0DXxPbFt5mRPi_GXQ7SPg_wfKqy1hM")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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

MESES_ES = {
    "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
    "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
    "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
}

MESES_NOMBRE = {
    "01": "ENERO", "02": "FEBRERO", "03": "MARZO", "04": "ABRIL",
    "05": "MAYO", "06": "JUNIO", "07": "JULIO", "08": "AGOSTO",
    "09": "SEPTIEMBRE", "10": "OCTUBRE", "11": "NOVIEMBRE", "12": "DICIEMBRE"
}

def categorizar(concepto):
    concepto_lower = concepto.lower()
    for cat, palabras in CATEGORIAS.items():
        for p in palabras:
            if p in concepto_lower:
                return cat
    return "🎯 Otros"

def parsear_gasto(texto):
    texto = texto.strip().replace("$", "").replace(",", "")
    patron1 = re.match(r'^(.+?)\s+(\d+(?:\.\d+)?)$', texto)
    patron2 = re.match(r'^(\d+(?:\.\d+)?)\s+(.+)$', texto)
    if patron1:
        return patron1.group(1).strip(), float(patron1.group(2))
    elif patron2:
        return patron2.group(2).strip(), float(patron2.group(1))
    return None, None

def fmt_monto(n):
    return f"${int(n):,}".replace(",", ".")

def hacer_resumen(gastos_mes, titulo):
    if not gastos_mes:
        return None
    total = sum(g["monto"] for g in gastos_mes)
    por_cat = {}
    for g in gastos_mes:
        cat = g["categoria"]
        por_cat[cat] = por_cat.get(cat, 0) + g["monto"]
    por_cat_sorted = sorted(por_cat.items(), key=lambda x: x[1], reverse=True)
    msg = f"📊 *{titulo}*\n{'─'*28}\n"
    for cat, monto in por_cat_sorted:
        pct = int(monto/total*100)
        barra = "█" * (pct//10) + "░" * (10-pct//10)
        msg += f"{cat}\n{barra} {fmt_monto(monto)} ({pct}%)\n\n"
    msg += f"{'─'*28}\n💰 *TOTAL: {fmt_monto(total)}*\n📅 {len(gastos_mes)} gastos"
    return msg

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 Hola {nombre}!\n\n"
        f"Mandame tus gastos así:\n"
        f"  *café 800*\n"
        f"  *almuerzo 1500*\n"
        f"  *nafta 8000*\n\n"
        f"📊 Comandos:\n"
        f"  /resumen — mes actual\n"
        f"  /resumen_mes mayo — mes específico\n"
        f"  /hoy — gastos de hoy\n"
        f"  /categorias — desglose por categoría\n"
        f"  /consejos — tips de ahorro\n"
        f"  /borrar_ultimo — borrar último gasto\n",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    texto = update.message.text.strip()
    concepto, monto = parsear_gasto(texto)
    if not concepto or not monto:
        await update.message.reply_text(
            "No entendí. Mandame el gasto así:\n*concepto monto* — ej: *café 800*",
            parse_mode="Markdown"
        )
        return
    categoria = categorizar(concepto)
    gasto = {
        "user_id": user_id,
        "concepto": concepto,
        "monto": monto,
        "categoria": categoria,
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "hora": datetime.now().strftime("%H:%M")
    }
    supabase.table("gastos").insert(gasto).execute()
    await update.message.reply_text(
        f"✓ *{concepto.capitalize()}* — {fmt_monto(monto)}\n📁 {categoria}",
        parse_mode="Markdown"
    )

async def resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    mes_actual = datetime.now().strftime("%Y-%m")
    res = supabase.table("gastos").select("*").eq("user_id", user_id).like("fecha", f"{mes_actual}%").execute()
    gastos_mes = res.data
    if not gastos_mes:
        await update.message.reply_text("No tenés gastos este mes.\nPara ver un mes anterior: /resumen_mes mayo")
        return
    mes_nombre = datetime.now().strftime("%B %Y").upper()
    msg = hacer_resumen(gastos_mes, f"RESUMEN {mes_nombre}")
    await update.message.reply_text(msg, parse_mode="Markdown")

async def resumen_mes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("Usalo así:\n  /resumen_mes mayo\n  /resumen_mes 5")
        return
    arg = context.args[0].lower()
    anio = datetime.now().strftime("%Y")
    if arg in MESES_ES:
        mes_num = MESES_ES[arg]
    elif arg.isdigit() and 1 <= int(arg) <= 12:
        mes_num = str(int(arg)).zfill(2)
    else:
        await update.message.reply_text("No reconocí el mes. Usá el nombre (mayo) o el número (5).")
        return
    mes_key = f"{anio}-{mes_num}"
    res = supabase.table("gastos").select("*").eq("user_id", user_id).like("fecha", f"{mes_key}%").execute()
    gastos_mes = res.data
    if not gastos_mes:
        await update.message.reply_text(f"No tenés gastos en {MESES_NOMBRE[mes_num]} {anio}.")
        return
    msg = hacer_resumen(gastos_mes, f"RESUMEN {MESES_NOMBRE[mes_num]} {anio}")
    await update.message.reply_text(msg, parse_mode="Markdown")

async def hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    res = supabase.table("gastos").select("*").eq("user_id", user_id).eq("fecha", hoy_str).execute()
    gastos_hoy = res.data
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
    mes_actual = datetime.now().strftime("%Y-%m")
    res = supabase.table("gastos").select("*").eq("user_id", user_id).like("fecha", f"{mes_actual}%").execute()
    gastos_mes = res.data
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
    mes_actual = datetime.now().strftime("%Y-%m")
    res = supabase.table("gastos").select("*").eq("user_id", user_id).like("fecha", f"{mes_actual}%").execute()
    gastos_mes = res.data
    if not gastos_mes:
        await update.message.reply_text("Registrá algunos gastos primero.")
        return
    total = sum(g["monto"] for g in gastos_mes)
    por_cat = {}
    for g in gastos_mes:
        por_cat[g["categoria"]] = por_cat.get(g["categoria"], 0) + g["monto"]
    top_cat = sorted(por_cat.items(), key=lambda x: x[1], reverse=True)[:3]
    msg = f"💡 *ANÁLISIS FINANCIERO*\n{'─'*28}\n\n💰 Gastaste *{fmt_monto(total)}* este mes\n\n🔴 *Top 3 categorías:*\n"
    for cat, monto in top_cat:
        pct = int(monto/total*100)
        msg += f"  {cat}: {fmt_monto(monto)} ({pct}%)\n"
    msg += f"\n💡 *Consejos:*\n"
    for cat, monto in top_cat:
        if "Salidas nocturnas" in cat and monto > 20000:
            msg += f"\n🌙 En salidas nocturnas gastás {fmt_monto(monto)}. Una salida menos por semana = {fmt_monto(monto*0.3)} ahorrados.\n"
        elif "Comida" in cat and monto > 30000:
            msg += f"\n🍔 En comida gastás {fmt_monto(monto)}. Cocinar 3 veces por semana te ahorra hasta {fmt_monto(monto*0.4)}.\n"
        elif "Salidas" in cat and monto > 25000:
            msg += f"\n🍽️ En salidas gastás {fmt_monto(monto)}. Invitar amigos a casa puede bajar esto a la mitad.\n"
        elif "Deudas" in cat:
            msg += f"\n💳 Tenés {fmt_monto(monto)} en deudas. Prioridad: pagar la de mayor tasa primero.\n"
        elif "Servicios" in cat:
            msg += f"\n📱 Gastás {fmt_monto(monto)} en suscripciones. Revisá cuáles realmente usás.\n"
    ahorro = total * 0.20
    msg += f"\n\n✅ *Potencial de ahorro: {fmt_monto(ahorro)}/mes*\n12 meses = *{fmt_monto(ahorro*12)}*"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def borrar_ultimo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    res = supabase.table("gastos").select("*").eq("user_id", user_id).order("id", desc=True).limit(1).execute()
    if not res.data:
        await update.message.reply_text("No tenés gastos registrados.")
        return
    ultimo = res.data[0]
    supabase.table("gastos").delete().eq("id", ultimo["id"]).execute()
    await update.message.reply_text(
        f"🗑️ Borrado: *{ultimo['concepto'].capitalize()}* — {fmt_monto(ultimo['monto'])}",
        parse_mode="Markdown"
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("resumen", resumen))
    app.add_handler(CommandHandler("resumen_mes", resumen_mes))
    app.add_handler(CommandHandler("hoy", hoy))
    app.add_handler(CommandHandler("categorias", categorias))
    app.add_handler(CommandHandler("consejos", consejos))
    app.add_handler(CommandHandler("borrar_ultimo", borrar_ultimo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot iniciado con Supabase...")
    app.run_polling()

if __name__ == "__main__":
    main()
