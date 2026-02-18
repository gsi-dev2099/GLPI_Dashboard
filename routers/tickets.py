from fastapi import APIRouter, Depends, Request, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db
from schemas import StatusCount
import hashlib
import resources

router = APIRouter(prefix="/api/tickets", tags=["tickets"])
templates = Jinja2Templates(directory=resources.get_path("templates"))

# --- SELECT COMÚN ---
# Columnas base para las listas detalladas (Inbox y Carousel)
BASE_SELECT_COLUMNS = """
    t.id AS ticket_id,
    t.name AS titulo,
    DATE_FORMAT(CONVERT_TZ(t.date, '+00:00', '-05:00'), '%d/%m/%Y %H:%i') AS fecha_hora,
    DATE_FORMAT(CONVERT_TZ(t.date, '+00:00', '-05:00'), '%Y-%m-%dT%H:%i:%s') AS fecha_iso,
    
    -- Solicitante
    (SELECT GROUP_CONCAT(CONCAT(u_req.realname, ' ', u_req.firstname) SEPARATOR ', ') 
     FROM glpi_tickets_users tu_req
     JOIN glpi_users u_req ON tu_req.users_id = u_req.id
     WHERE tu_req.tickets_id = t.id AND tu_req.type = 1) AS solicitante,
     
    -- Técnico (Lógica SD - Sin Texto (SD))
    TRIM(BOTH ', ' FROM CONCAT_WS(', ', 
        (SELECT GROUP_CONCAT(
            CONCAT(u_tech.realname, ' ', u_tech.firstname) SEPARATOR ', ') 
         FROM glpi_tickets_users tu_tech
         JOIN glpi_users u_tech ON tu_tech.users_id = u_tech.id
         WHERE tu_tech.tickets_id = t.id AND tu_tech.type = 2),
         
        (SELECT GROUP_CONCAT(g_tech.name SEPARATOR ', ') 
         FROM glpi_groups_tickets gt
         JOIN glpi_groups g_tech ON gt.groups_id = g_tech.id
         WHERE gt.tickets_id = t.id AND gt.type = 2)
    )) AS tecnico,
    
    -- Bandera SD
    (
        EXISTS(
            SELECT 1 FROM glpi_tickets_users tu 
            JOIN glpi_groups_users gu ON tu.users_id = gu.users_id
            JOIN glpi_groups g ON gu.groups_id = g.id
            WHERE tu.tickets_id = t.id AND tu.type = 2 
            AND (g.name LIKE '%Service Desk%' OR g.name LIKE '%Soporte%')
        ) OR EXISTS(
            SELECT 1 FROM glpi_groups_tickets gt
            JOIN glpi_groups g ON gt.groups_id = g.id
            WHERE gt.tickets_id = t.id AND gt.type = 2
            AND (g.name LIKE '%Service Desk%' OR g.name LIKE '%Soporte%')
        )
    ) AS es_soporte_sd,

    -- Bandera Tiene Técnico Humano
    (SELECT COUNT(*) FROM glpi_tickets_users tu 
     WHERE tu.tickets_id = t.id AND tu.type = 2) > 0 AS tiene_tecnico,

    TIMESTAMPDIFF(MINUTE, t.date, UTC_TIMESTAMP()) AS minutos_transcurridos,
    
    CASE t.status
        WHEN 1 THEN 'Nuevo'
        WHEN 2 THEN 'Asignado'
        WHEN 3 THEN 'Planificado'
        WHEN 4 THEN 'En espera'
        WHEN 5 THEN 'Resuelto'
        WHEN 6 THEN 'Cerrado'
        WHEN 10 THEN 'Esperando Aprobación'
        ELSE 'Otro'
    END AS estado,
    t.status AS status_id
"""

@router.get("/stats")
async def get_ticket_stats(request: Request, db: AsyncSession = Depends(get_db)):
    """ 
    CONSULTA 1: Estadísticas (Counts)
    """
    try:
        rows = await fetch_ticket_stats(db)
        # Mapeamos los resultados (dicts) al esquema StatusCount
        counts = [StatusCount(estado=row['estado'], total=row['total']) for row in rows]

        return templates.TemplateResponse("ticket_cards.html", {"request": request, "counts": counts})
    except Exception as e:
        print(f"Error in stats: {e}")
        return templates.TemplateResponse("error_fragment.html", {"request": request, "message": "Error BD Stats"})

@router.get("/inbox")
async def get_inbox(request: Request, db: AsyncSession = Depends(get_db)):
    """ 
    CONSULTA 2: Fijos (Inbox) - Solo Nuevos sin Asignar
    """
    try:
        tickets_inbox = await fetch_inbox_tickets(db)
        
        # Hash Generation para evitar recargas innecesarias
        data_string = "".join([f"{t['ticket_id']}-{t['status_id']}" for t in tickets_inbox])
        current_hash = hashlib.md5(data_string.encode('utf-8')).hexdigest()
        
        if request.cookies.get("inbox_hash") == current_hash:
            return Response(status_code=204)
        
        response = templates.TemplateResponse("inbox_fragment.html", {"request": request, "tickets": tickets_inbox})
        response.set_cookie(key="inbox_hash", value=current_hash, httponly=True)
        return response
    except Exception as e:
        print(f"Error in inbox: {e}")
        return templates.TemplateResponse("error_fragment.html", {"request": request, "message": "Error Inbox"})

@router.get("/carousel")
async def get_carousel(request: Request, db: AsyncSession = Depends(get_db)):
    """ 
    CONSULTA 3: Carrusel - Tickets en Proceso
    """
    try:
        tickets_carousel = await fetch_carousel_tickets(db)
        
        # Hash Generation
        data_string = "".join([f"{t['ticket_id']}-{t['status_id']}" for t in tickets_carousel])
        current_hash = hashlib.md5(data_string.encode('utf-8')).hexdigest()
        
        if request.cookies.get("carousel_hash") == current_hash:
            return Response(status_code=204)
        
        response = templates.TemplateResponse("carousel_fragment.html", {"request": request, "tickets": tickets_carousel})
        response.set_cookie(key="carousel_hash", value=current_hash, httponly=True)
        return response
    except Exception as e:
        print(f"Error in carousel: {e}")
        return templates.TemplateResponse("error_fragment.html", {"request": request, "message": "Error Carrusel"})

# --- FUNCIONES DE BASE DE DATOS (Las 3 Consultas) ---

async def fetch_ticket_stats(db: AsyncSession):
    """
    1. CONSULTA DE CONTEOS
    Agrupa por estado y cuenta el total.
    """
    sql = text("""
        SELECT 
            CASE status
                WHEN 1 THEN 'Nuevo'
                WHEN 2 THEN 'Asignado'
                WHEN 3 THEN 'Planificado'
                WHEN 4 THEN 'En espera'
                WHEN 5 THEN 'Resuelto'
                WHEN 6 THEN 'Cerrado'
                WHEN 10 THEN 'Esperando Aprobación'
                ELSE 'Otro'
            END AS estado,
            COUNT(id) AS total
        FROM glpi_tickets
        WHERE is_deleted = 0
          AND (
            status != 6  -- Para otros estados, cuenta todo
            OR (
                status = 6 -- Para Cerrado, solo los de HOY (Zona Horaria -05:00)
                AND DATE(CONVERT_TZ(closedate, '+00:00', '-05:00')) = DATE(CONVERT_TZ(UTC_TIMESTAMP(), '+00:00', '-05:00'))
            )
          )
        GROUP BY status
        ORDER BY total DESC
    """)
    result = await db.execute(sql)
    return result.mappings().all()

async def fetch_inbox_tickets(db: AsyncSession):
    """
    2. CONSULTA DE FIJOS (INBOX)
    Trae SOLO tickets Nuevos (1) que NO tienen técnico humano asignado.
    """
    sql = text(f"""
        SELECT {BASE_SELECT_COLUMNS}
        FROM glpi_tickets t
        WHERE t.is_deleted = 0 
          AND t.status = 1  -- Solo Nuevos
          AND (
            -- Subconsulta para verificar que NO existe técnico humano (type=2)
            NOT EXISTS (
                SELECT 1 FROM glpi_tickets_users tu 
                WHERE tu.tickets_id = t.id AND tu.type = 2
            )
          )
        ORDER BY t.date DESC
    """)
    result = await db.execute(sql)
    return result.mappings().all()

async def fetch_carousel_tickets(db: AsyncSession):
    """
    3. CONSULTA DE CARRUSEL
    Trae el RESTO de tickets activos (Asignados, En proceso, Espera, etc).
    """
    sql = text(f"""
        SELECT {BASE_SELECT_COLUMNS}
        FROM glpi_tickets t
        WHERE t.is_deleted = 0 
          AND t.status != 6 -- Ignorar Cerrados del carrusel si se desea
          AND (
            t.status != 1 -- Si no es nuevo, entra al carrusel
            OR 
            (
                -- Si ES nuevo, solo entra si YA tiene técnico asignado
                t.status = 1 AND EXISTS (
                    SELECT 1 FROM glpi_tickets_users tu 
                    WHERE tu.tickets_id = t.id AND tu.type = 2
                )
            )
          )
        ORDER BY 
            CASE t.status
                WHEN 1 THEN 1 -- Nuevo con técnico (Prioridad alta)
                WHEN 10 THEN 2 -- Aprobación
                WHEN 2 THEN 3 -- Asignado
                WHEN 3 THEN 3 -- Planificado
                WHEN 4 THEN 4 -- En espera
                ELSE 5 
            END ASC,
            t.date DESC
        LIMIT 50
    """)
    result = await db.execute(sql)
    return result.mappings().all()

@router.get("/members")
async def get_members(request: Request, db: AsyncSession = Depends(get_db)):
    """ 
    CONSULTA 4: Integrantes Service Desk
    """
    try:
        members = await fetch_members(db)
        return templates.TemplateResponse("members_fragment.html", {"request": request, "members": members})
    except Exception as e:
        print(f"Error in members: {e}")
        return "" # Fail silently or show nothing if error

async def fetch_members(db: AsyncSession):
    """
    4. CONSULTA DE INTEGRANTES
    Trae técnicos de Service Desk y cuenta sus tickets activos.
    """
    sql = text("""
        SELECT DISTINCT
            u.id AS user_id,
            CONCAT(u.realname, ' ', u.firstname) AS nombre_completo,
            u.name AS usuario,
            g.name AS grupo,
            -- Conteo de tickets activos (Ni resueltos ni cerrados)
            (SELECT COUNT(*) 
             FROM glpi_tickets_users tu
             INNER JOIN glpi_tickets t ON tu.tickets_id = t.id
             WHERE tu.users_id = u.id 
               AND tu.type = 2 -- Rol de Técnico
               AND t.is_deleted = 0
               AND t.status NOT IN (5, 6) -- 5=Resuelto, 6=Cerrado
            ) AS tickets_activos
        FROM glpi_users u
        JOIN glpi_groups_users gu ON gu.users_id = u.id
        JOIN glpi_groups g ON gu.groups_id = g.id
        WHERE (g.name LIKE '%Service Desk%' OR g.name LIKE '%Soporte%')
          AND u.is_deleted = 0 
          AND u.is_active = 1
        ORDER BY tickets_activos ASC, u.realname ASC
    """)
    result = await db.execute(sql)
    return result.mappings().all()