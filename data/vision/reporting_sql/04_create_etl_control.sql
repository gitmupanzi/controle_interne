/*
  BB_VISION_REPORTING - controle ETL et rapprochements
*/

USE BB_VISION_REPORTING;
GO

IF OBJECT_ID(N'ctl.etl_batch', N'U') IS NULL
BEGIN
    CREATE TABLE ctl.etl_batch (
        batch_id bigint IDENTITY(1,1) NOT NULL CONSTRAINT pk_ctl_etl_batch PRIMARY KEY,
        source_database sysname NOT NULL,
        date_debut date NOT NULL,
        date_fin date NOT NULL,
        id_devise_reporting int NULL,
        started_at datetime2(0) NOT NULL CONSTRAINT df_ctl_etl_batch_started DEFAULT (sysdatetime()),
        ended_at datetime2(0) NULL,
        status varchar(30) NOT NULL CONSTRAINT df_ctl_etl_batch_status DEFAULT ('RUNNING'),
        message varchar(2000) NULL
    );
END;
GO

IF OBJECT_ID(N'ctl.etl_table_log', N'U') IS NULL
BEGIN
    CREATE TABLE ctl.etl_table_log (
        table_log_id bigint IDENTITY(1,1) NOT NULL CONSTRAINT pk_ctl_etl_table_log PRIMARY KEY,
        batch_id bigint NOT NULL,
        schema_name sysname NOT NULL,
        table_name sysname NOT NULL,
        started_at datetime2(0) NOT NULL CONSTRAINT df_ctl_etl_table_log_started DEFAULT (sysdatetime()),
        ended_at datetime2(0) NULL,
        rows_inserted bigint NULL,
        status varchar(30) NOT NULL CONSTRAINT df_ctl_etl_table_log_status DEFAULT ('RUNNING'),
        message varchar(2000) NULL
    );
END;
GO

IF OBJECT_ID(N'ctl.kpi_reconciliation', N'U') IS NULL
BEGIN
    CREATE TABLE ctl.kpi_reconciliation (
        reconciliation_id bigint IDENTITY(1,1) NOT NULL CONSTRAINT pk_ctl_kpi_reconciliation PRIMARY KEY,
        batch_id bigint NULL,
        page_name varchar(255) NOT NULL,
        visual_name varchar(255) NULL,
        kpi_name varchar(255) NOT NULL,
        powerbi_measure varchar(255) NULL,
        sql_reference_query int NULL,
        date_debut date NULL,
        date_fin date NULL,
        devise varchar(10) NULL,
        sql_value decimal(28,6) NULL,
        powerbi_value decimal(28,6) NULL,
        difference AS (powerbi_value - sql_value),
        status varchar(30) NULL,
        checked_at datetime2(0) NOT NULL CONSTRAINT df_ctl_kpi_reconciliation_checked DEFAULT (sysdatetime()),
        comment varchar(2000) NULL
    );
END;
GO

CREATE OR ALTER PROCEDURE ctl.start_batch
    @source_database sysname,
    @date_debut date,
    @date_fin date,
    @id_devise_reporting int = NULL,
    @batch_id bigint OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    INSERT INTO ctl.etl_batch (source_database, date_debut, date_fin, id_devise_reporting)
    VALUES (@source_database, @date_debut, @date_fin, @id_devise_reporting);

    SET @batch_id = SCOPE_IDENTITY();
END;
GO

CREATE OR ALTER PROCEDURE ctl.end_batch
    @batch_id bigint,
    @status varchar(30),
    @message varchar(2000) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE ctl.etl_batch
    SET ended_at = sysdatetime(),
        status = @status,
        message = @message
    WHERE batch_id = @batch_id;
END;
GO
