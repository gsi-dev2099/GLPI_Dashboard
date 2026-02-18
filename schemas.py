from pydantic import BaseModel, ConfigDict

class StatusCount(BaseModel):
    estado: str
    total: int

    model_config = ConfigDict(from_attributes=True)

class DashboardData(BaseModel):
    counts: list[StatusCount]
    total_tickets: int

class TicketDetail(BaseModel):
    ticket_id: int
    titulo: str
    fecha_hora: str
    solicitante: str | None = None
    tecnico: str | None = None
    estado: str

    model_config = ConfigDict(from_attributes=True)
