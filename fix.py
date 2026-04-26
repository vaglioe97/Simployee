import sqlite3
conn = sqlite3.connect('data/simployee.db')
conn.execute("DELETE FROM tasks WHERE week=1")
conn.commit()
conn.close()
print('Tasks cleared')