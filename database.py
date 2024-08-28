import sqlite3
import aiosqlite

def get_connection():
    conn = sqlite3.connect('burgers.db')
    return conn

async def async_get_connection():
    return await aiosqlite.connect('burgers.db')

def init_db():
    with get_connection() as conn:
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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_states (
                user_id INTEGER PRIMARY KEY,
                state TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_quantities (
                user_id INTEGER PRIMARY KEY,
                quantity INTEGER NOT NULL DEFAULT 1
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_remove_states (
                user_id INTEGER PRIMARY KEY,
                burger_id INTEGER,
                quantity INTEGER
            )
        ''')
        conn.commit()

def get_burgers():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM burgers')
        burgers = cursor.fetchall()
        print(f"Burgers fetched: {burgers}")
        return burgers

def remove_burger(burger_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM burgers WHERE id = ?', (burger_id,))
        conn.commit()

def add_to_cart(user_id, burger_id, quantity):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO cart (user_id, burger_id, quantity) VALUES (?, ?, ?)',
                           (user_id, burger_id, quantity))
            conn.commit()
            print(f"Added to cart: user_id={user_id}, burger_id={burger_id}, quantity={quantity}")
    except Exception as e:
        print(f"Error adding to cart: {e}")

def get_cart(user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.id, b.name, b.description, b.price, c.quantity
            FROM cart c
            JOIN burgers b ON c.burger_id = b.id
            WHERE c.user_id = ?
        ''', (user_id,))
        cart_items = cursor.fetchall()
        return cart_items

def remove_from_cart(user_id, burger_id, quantity):
    if not isinstance(user_id, int) or not isinstance(burger_id, int) or not isinstance(quantity, int):
        raise ValueError("Invalid data format")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT quantity FROM cart WHERE user_id = ? AND burger_id = ?', (user_id, burger_id))
        result = cursor.fetchone()
        if result:
            current_quantity = result[0]
            new_quantity = max(current_quantity - quantity, 0)
            if new_quantity == 0:
                cursor.execute('DELETE FROM cart WHERE user_id = ? AND burger_id = ?', (user_id, burger_id))
            else:
                cursor.execute('UPDATE cart SET quantity = ? WHERE user_id = ? AND burger_id = ?',
                               (new_quantity, user_id, burger_id))
        conn.commit()
        print(f"Removed from cart: user_id={user_id}, burger_id={burger_id}, quantity={quantity}")

def save_user_state(user_id, state):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('REPLACE INTO user_states (user_id, state) VALUES (?, ?)', (user_id, state))
        conn.commit()

def get_user_state(user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT state FROM user_states WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else None

def save_user_quantity(user_id, quantity):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('REPLACE INTO user_quantities (user_id, quantity) VALUES (?, ?)', (user_id, quantity))
        conn.commit()

def get_user_quantity(user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT quantity FROM user_quantities WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else None

def save_user_remove_burger_id(user_id, burger_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('REPLACE INTO user_remove_states (user_id, burger_id) VALUES (?, ?)', (user_id, burger_id))
        conn.commit()

def get_user_remove_burger_id(user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT burger_id FROM user_remove_states WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else None

def save_user_remove_quantity(user_id, quantity):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('REPLACE INTO user_remove_states (user_id, quantity) VALUES (?, ?)', (user_id, quantity))
        conn.commit()

def get_user_remove_quantity(user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT quantity FROM user_remove_states WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else None

# Асинхронные функции для работы с базой данных

async def async_remove_from_cart(user_id, burger_id, quantity):
    async with aiosqlite.connect('burgers.db') as db:
        cursor = await db.execute('SELECT quantity FROM cart WHERE user_id = ? AND burger_id = ?', (user_id, burger_id))
        result = await cursor.fetchone()
        if result:
            current_quantity = result[0]
            new_quantity = max(current_quantity - quantity, 0)
            if new_quantity == 0:
                await db.execute('DELETE FROM cart WHERE user_id = ? AND burger_id = ?', (user_id, burger_id))
            else:
                await db.execute('UPDATE cart SET quantity = ? WHERE user_id = ? AND burger_id = ?',
                                 (new_quantity, user_id, burger_id))
        await db.commit()

async def async_add_to_cart(user_id, burger_id, quantity):
    async with aiosqlite.connect('burgers.db') as db:
        await db.execute('INSERT INTO cart (user_id, burger_id, quantity) VALUES (?, ?, ?)',
                         (user_id, burger_id, quantity))
        await db.commit()

async def async_get_cart(user_id):
    async with aiosqlite.connect('burgers.db') as db:
        cursor = await db.execute('''
            SELECT b.id, b.name, b.description, b.price, c.quantity
            FROM cart c
            JOIN burgers b ON c.burger_id = b.id
            WHERE c.user_id = ?
        ''', (user_id,))
        cart_items = await cursor.fetchall()
        return cart_items

async def async_get_burgers():
    async with aiosqlite.connect('burgers.db') as db:
        async with db.execute('SELECT * FROM burgers') as cursor:
            burgers = await cursor.fetchall()
            return burgers

async def async_remove_burger(burger_id):
    async with aiosqlite.connect('burgers.db') as db:
        await db.execute('DELETE FROM burgers WHERE id = ?', (burger_id,))
        await db.commit()

async def async_save_user_state(user_id, state):
    async with aiosqlite.connect('burgers.db') as db:
        await db.execute('REPLACE INTO user_states (user_id, state) VALUES (?, ?)', (user_id, state))
        await db.commit()

async def async_get_user_state(user_id):
    async with aiosqlite.connect('burgers.db') as db:
        async with db.execute('SELECT state FROM user_states WHERE user_id = ?', (user_id,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None

async def async_save_user_quantity(user_id, quantity):
    async with aiosqlite.connect('burgers.db') as db:
        await db.execute('REPLACE INTO user_quantities (user_id, quantity) VALUES (?, ?)', (user_id, quantity))
        await db.commit()

async def async_get_user_quantity(user_id):
    async with aiosqlite.connect('burgers.db') as db:
        async with db.execute('SELECT quantity FROM user_quantities WHERE user_id = ?', (user_id,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None

async def async_save_user_remove_burger_id(user_id, burger_id):
    async with aiosqlite.connect('burgers.db') as db:
        await db.execute('REPLACE INTO user_remove_states (user_id, burger_id) VALUES (?, ?)', (user_id, burger_id))
        await db.commit()

async def async_get_user_remove_burger_id(user_id):
    async with aiosqlite.connect('burgers.db') as db:
        async with db.execute('SELECT burger_id FROM user_remove_states WHERE user_id = ?', (user_id,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None

async def async_save_user_remove_quantity(user_id, quantity):
    async with aiosqlite.connect('burgers.db') as db:
        await db.execute('REPLACE INTO user_remove_states (user_id, quantity) VALUES (?, ?)', (user_id, quantity))
        await db.commit()

async def async_get_user_remove_quantity(user_id):
    async with aiosqlite.connect('burgers.db') as db:
        async with db.execute('SELECT quantity FROM user_remove_states WHERE user_id = ?', (user_id,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None
