/*
 SQLite triggers: row-level audit for Pets/Appointments and appointment conflict rule.
*/
CREATE TRIGGER IF NOT EXISTS trg_Pets_Audit_Insert AFTER INSERT ON Pets BEGIN
 INSERT INTO AuditLog(TableName,Operation,Data,Username)
 VALUES('Pets','INSERT',json_object('PetID',NEW.PetID,'PetName',NEW.PetName,'OwnerID',NEW.OwnerID),'application');
END;
CREATE TRIGGER IF NOT EXISTS trg_Pets_Audit_Update AFTER UPDATE ON Pets BEGIN
 INSERT INTO AuditLog(TableName,Operation,Data,Username)
 VALUES('Pets','UPDATE',json_object('PetID',NEW.PetID,'OldName',OLD.PetName,'NewName',NEW.PetName,'OwnerID',NEW.OwnerID),'application');
END;
CREATE TRIGGER IF NOT EXISTS trg_Pets_Audit_Delete AFTER DELETE ON Pets BEGIN
 INSERT INTO AuditLog(TableName,Operation,Data,Username)
 VALUES('Pets','DELETE',json_object('PetID',OLD.PetID,'PetName',OLD.PetName,'OwnerID',OLD.OwnerID),'application');
END;
CREATE TRIGGER IF NOT EXISTS trg_Appointments_Audit_Insert AFTER INSERT ON Appointments BEGIN
 INSERT INTO AuditLog(TableName,Operation,Data,Username)
 VALUES('Appointments','INSERT',json_object('AppointmentID',NEW.AppointmentID,'PetID',NEW.PetID,'StartAt',NEW.StartAt,'Kind',NEW.Kind),'application');
END;
CREATE TRIGGER IF NOT EXISTS trg_Appointments_Audit_Update AFTER UPDATE ON Appointments BEGIN
 INSERT INTO AuditLog(TableName,Operation,Data,Username)
 VALUES('Appointments','UPDATE',json_object('AppointmentID',NEW.AppointmentID,'OldStatus',OLD.Status,'NewStatus',NEW.Status,'StartAt',NEW.StartAt),'application');
END;
CREATE TRIGGER IF NOT EXISTS trg_Appointments_Audit_Delete AFTER DELETE ON Appointments BEGIN
 INSERT INTO AuditLog(TableName,Operation,Data,Username)
 VALUES('Appointments','DELETE',json_object('AppointmentID',OLD.AppointmentID,'PetID',OLD.PetID,'StartAt',OLD.StartAt),'application');
END;
/* A pet cannot have two active bookings within 30 minutes. */
CREATE TRIGGER IF NOT EXISTS trg_Appointments_NoOverlap_Insert BEFORE INSERT ON Appointments
WHEN NEW.Status='Запланирован' AND EXISTS(
 SELECT 1 FROM Appointments a WHERE a.PetID=NEW.PetID AND a.Status='Запланирован'
 AND a.StartAt < datetime(NEW.StartAt,'+30 minutes') AND NEW.StartAt < datetime(a.StartAt,'+30 minutes'))
BEGIN SELECT RAISE(ABORT,'У питомца уже есть запись в пределах 30 минут от выбранного времени.'); END;
CREATE TRIGGER IF NOT EXISTS trg_Appointments_NoOverlap_Update BEFORE UPDATE OF PetID,StartAt,Status ON Appointments
WHEN NEW.Status='Запланирован' AND EXISTS(
 SELECT 1 FROM Appointments a WHERE a.PetID=NEW.PetID AND a.AppointmentID<>NEW.AppointmentID
 AND a.Status='Запланирован' AND a.StartAt < datetime(NEW.StartAt,'+30 minutes')
 AND NEW.StartAt < datetime(a.StartAt,'+30 minutes'))
BEGIN SELECT RAISE(ABORT,'У питомца уже есть запись в пределах 30 минут от выбранного времени.'); END;
