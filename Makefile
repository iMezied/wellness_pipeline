# ════════════════════════════════════════════════════════════
# Makefile — اختصارات للأوامر الشائعة
# الاستخدام: make <command>
# ════════════════════════════════════════════════════════════

.PHONY: help setup up down restart logs test shell db-shell clean

# ── المساعدة ─────────────────────────────────────────────
help:
	@echo ""
	@echo "  Wellness Pipeline — Docker Commands"
	@echo "  ────────────────────────────────────"
	@echo "  make setup    → أول مرة: إنشاء .env وبناء الـ images"
	@echo "  make up       → تشغيل كل الخدمات"
	@echo "  make down     → إيقاف كل الخدمات"
	@echo "  make restart  → إعادة تشغيل الـ pipeline فقط"
	@echo "  make logs     → متابعة لوق الـ pipeline"
	@echo "  make test     → تشغيل فيديو واحد للاختبار"
	@echo "  make shell    → دخول shell داخل الـ pipeline container"
	@echo "  make db-shell → دخول MySQL shell"
	@echo "  make clean    → حذف كل شيء (containers + volumes)"
	@echo ""

# ── الإعداد الأول ──────────────────────────────────────────
setup:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ تم إنشاء .env — افتحه وعبّئ القيم قبل المتابعة"; \
	else \
		echo "⚠️  .env موجود مسبقاً"; \
	fi
	docker compose build

# ── التشغيل ────────────────────────────────────────────────
up:
	docker compose up -d
	@echo "✅ الخدمات شغّالة"
	@echo "   Dashboard DB: http://localhost:8080"
	@echo "   Server: db | System: MySQL | User: $$(grep DB_USER .env | cut -d= -f2)"

down:
	docker compose down

restart:
	docker compose restart pipeline

# ── المراقبة ───────────────────────────────────────────────
logs:
	docker compose logs -f pipeline

logs-all:
	docker compose logs -f

status:
	docker compose ps

# ── الاختبار ───────────────────────────────────────────────
test:
	@echo "🧪 تشغيل فيديو واحد للاختبار..."
	docker compose exec pipeline python3 pipeline.py once

# ── الدخول للـ containers ──────────────────────────────────
shell:
	docker compose exec pipeline bash

db-shell:
	docker compose exec db mysql -u $$(grep DB_USER .env | cut -d= -f2) \
		-p$$(grep DB_PASS .env | cut -d= -f2) $$(grep DB_NAME .env | cut -d= -f2)

# ── الإنتاج ────────────────────────────────────────────────
build:
	docker compose build --no-cache

pull:
	docker compose pull

deploy: pull build
	docker compose up -d
	@echo "✅ Deployed"

# ── التنظيف ────────────────────────────────────────────────
clean:
	@echo "⚠️  سيحذف هذا كل شيء بما فيه قاعدة البيانات!"
	@read -p "متأكد؟ (yes/no): " confirm && [ "$$confirm" = "yes" ]
	docker compose down -v --remove-orphans
	docker image rm wellness_pipeline_pipeline 2>/dev/null || true
	@echo "✅ تم التنظيف"
