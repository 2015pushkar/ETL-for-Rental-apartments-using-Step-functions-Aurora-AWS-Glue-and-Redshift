# 🏡 Rental Apartments ETL — Visual README

> **A picture‑first overview** of our Aurora → Redshift pipeline, orchestrated by AWS Step Functions and powered by AWS Glue.

---

## 1  System Architecture

![Architecture](images/system_architecture.png)

---

## 2  State‑Machine Orchestration

![State Machine](images/stepfunctions_graph.png)

---

## 3  Six‑Step Data Flow

|  #  | Stage          | What Happens                   | Visual                                                    |
| :-: | -------------- | ------------------------------ | --------------------------------------------------------- |
|  1  | **Extract**    | Aurora MySQL → S3 *raw*        | ![](images/aurora_to_s3_data_extracted.png)               |
|  2  | **Raw Ingest** | Glue COPY → Redshift *tmp*     | ![](images/redshift_raw_ingestion_success.png)            |
|  3  | **Transform**  | Glue Spark → curated CSV       | ![](images/data_processed_from_raw_to_curated.png)        |
|  4  | **Load**       | MERGE → Redshift schemas       | ![](images/data_ingested_redshift.png)                    |
|  5  | **Bookmark**   | Write latest offset → DynamoDB | ![](images/dynamo_db_incremental_data_update.png)         |
|  6  | **Finalize**   | Query curated tables           | ![](images/processed_Data_in_redshifts_curated_layer.png) |

---

## 4  AWS Building Blocks

* **Aurora (MySQL)** – source data
* **Amazon S3** – raw & curated storage
* **AWS Glue** – Python Shell + Spark ETL
* **DynamoDB** – incremental bookmarks
* **Step Functions** – workflow engine
* **Redshift** – analytics warehouse

---

## 5  Quick Start (3 Commands)

```bash
# 1. Seed DynamoDB bookmarks
python write-to-dynamo.py

# 2. Upload Glue scripts (once)
aws s3 sync glue/ s3://<your-assets-bucket>/scripts/

# 3. Deploy Step Function
aws stepfunctions create-state-machine \
  --definition file://step-functions/step-functions.json \
  --role-arn <your-sfn-role>
```

Run the state machine in the console and watch CloudWatch Logs for progress.

---

## 6  Repo Layout

```
├─ data/                  CSV samples
├─ glue/                  Glue jobs
├─ images/                All diagrams & screenshots
├─ mysql/                 MySQL DDL / queries
├─ redshift/              Redshift DDL
├─ step-functions/        State‑machine JSON
├─ write-to-dynamo.py     Bookmark seeder
└─ README.md              (this file)
```

---

*Built with AWS Serverless & Analytics Services*
