const express = require('express');
const mysql = require('mysql2');
const path = require('path');

const app = express();
const port = process.env.PORT || 3000;

// 미들웨어 설정
app.use(express.json());
app.use(express.static(path.join(__dirname, '../public')));
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// 데이터베이스 연결 설정
const db = mysql.createConnection({
  host: process.env.DB_HOST || 'source-db-service',
  user: process.env.DB_USER || 'root',
  password: process.env.DB_PASSWORD || '1234',
  database: process.env.DB_NAME || 'kopo'
});

// 라우트 설정
app.get('/', (req, res) => {
  res.render('dashboard');
});

// ETL 상태 조회 API
app.get('/api/etl-status', async (req, res) => {
  try {
    const [rows] = await db.promise().query('SELECT * FROM 데이터셋_최신화_이력 ORDER BY created_at DESC LIMIT 10');
    res.json(rows);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 위해상품 데이터 조회 API
app.get('/api/dangerous-products', async (req, res) => {
  try {
    const [rows] = await db.promise().query('SELECT * FROM 위해상품_위험도_분석 LIMIT 100');
    res.json(rows);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.listen(port, () => {
  console.log(`Server is running on port ${port}`);
}); 