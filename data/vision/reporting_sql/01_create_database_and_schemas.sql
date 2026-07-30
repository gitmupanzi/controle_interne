/*
  BB_VISION_REPORTING - creation base et schemas

  A executer avec un compte autorise a creer une base.
  Le script est idempotent : il ne supprime aucune base et ne modifie pas Perfect Vision.
*/

IF DB_ID(N'BB_VISION_REPORTING') IS NULL
BEGIN
    EXEC(N'CREATE DATABASE BB_VISION_REPORTING;');
END;
GO

USE BB_VISION_REPORTING;
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'rpt')
    EXEC(N'CREATE SCHEMA rpt');
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'pbi')
    EXEC(N'CREATE SCHEMA pbi');
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'ctl')
    EXEC(N'CREATE SCHEMA ctl');
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'stg')
    EXEC(N'CREATE SCHEMA stg');
GO
