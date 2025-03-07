#!/bin/sh
cd /app/

# List all environment variables
echo "----------LISTING ALL ENVIRONMENT VARIABLES----------"
# env

echo "----------INITIALIZE DATABASE------------------"
python init.py

echo "service_port: ${SERVICE_PORT}"

echo "------    STARTING GUNICORN AT $SERVICE_HOST:${SERVICE_PORT}  --"
if [ "$SERVICE_RELOAD" = "true" ]; then
    uvicorn api:app --host "$SERVICE_HOST" --port "$SERVICE_PORT" --workers $SERVICE_WORKERS --reload
elif [ "$SERVICE_RELOAD" = "false" ]; then
    uvicorn api:app --host "$SERVICE_HOST" --port "$SERVICE_PORT" --workers $SERVICE_WORKERS
else
    uvicorn api:app --host "$SERVICE_HOST" --port "$SERVICE_PORT" --workers $SERVICE_WORKERS
fi