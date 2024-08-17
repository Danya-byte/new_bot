import sqlite3
import aiosqlite


def init_db():
    conn = sqlite3.connect('burgers.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS burgers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            user_id INTEGER NOT NULL,
            burger_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (burger_id) REFERENCES burgers (id)
        )
    ''')
    conn.commit()
    conn.close()

def get_burgers():
    conn = sqlite3.connect('burgers.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM burgers')
    burgers = cursor.fetchall()
    conn.close()
    return burgers

def remove_burger(burger_id):
    conn = sqlite3.connect('burgers.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM burgers WHERE id = ?', (burger_id,))
    conn.commit()
    conn.close()

def add_to_cart(user_id, burger_id, quantity):
    conn = sqlite3.connect('burgers.db')
    cursor = conn.cursor()
    cursor.execute('SELECT quantity FROM cart WHERE user_id = ? AND burger_id = ?', (user_id, burger_id))
    result = cursor.fetchone()
    if result:
        current_quantity = result[0]
        new_quantity = current_quantity + quantity
        cursor.execute('UPDATE cart SET quantity = ? WHERE user_id = ? AND burger_id = ?', (new_quantity, user_id, burger_id))
    else:
        cursor.execute('INSERT INTO cart (user_id, burger_id, quantity) VALUES (?, ?, ?)', (user_id, burger_id, quantity))
    conn.commit()
    conn.close()

def get_cart(user_id):
    conn = sqlite3.connect('burgers.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT b.id, b.name, b.description, b.price, c.quantity
        FROM cart c
        JOIN burgers b ON c.burger_id = b.id
        WHERE c.user_id = ?
    ''', (user_id,))
    cart_items = cursor.fetchall()
    conn.close()
    return cart_items

def remove_from_cart(user_id, burger_id, quantity):
    conn = sqlite3.connect('burgers.db')
    cursor = conn.cursor()
    cursor.execute('SELECT quantity FROM cart WHERE user_id = ? AND burger_id = ?', (user_id, burger_id))
    result = cursor.fetchone()
    if result:
        current_quantity = result[0]
        new_quantity = max(current_quantity - quantity, 0)
        if new_quantity == 0:
            cursor.execute('DELETE FROM cart WHERE user_id = ? AND burger_id = ?', (user_id, burger_id))
        else:
            cursor.execute('UPDATE cart SET quantity = ? WHERE user_id = ? AND burger_id = ?', (new_quantity, user_id, burger_id))
    conn.commit()
    conn.close()

# Асинхронные функции для работы с базой данных

async def async_get_burgers():
    async with aiosqlite.connect('burgers.db') as db:
        async with db.execute('SELECT * FROM burgers') as cursor:
            return await cursor.fetchall()

async def async_remove_burger(burger_id):
    async with aiosqlite.connect('burgers.db') as db:
        await db.execute('DELETE FROM burgers WHERE id = ?', (burger_id,))
        await db.commit()