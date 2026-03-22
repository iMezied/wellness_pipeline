-- يُنفَّذ تلقائياً عند أول تشغيل للـ container
-- قاعدة البيانات تُنشأ تلقائياً من MYSQL_DATABASE في docker-compose
-- هذا الملف للـ charset فقط

ALTER DATABASE wellness_pipeline CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
