# Databricks notebook source
# SparkSession이 이미 생성되어 있어야 합니다.
df_member = spark.read.format("delta").load("dbfs:/user/hive/warehouse/database_pjt.db/df_final_with_cluster")

df_customer = spark.read.format("delta").load("dbfs:/user/hive/warehouse/database_pjt.db/customer_clusters_final")

# COMMAND ----------

display(df_member.limit(3))

# COMMAND ----------

display(df_customer.limit(3))

# COMMAND ----------

# 중복 제거 (필요한 컬럼만 유지)
df_member_unique = df_member.select("발급회원번호", "cluster").dropDuplicates()
df_customer_unique = df_customer.select("발급회원번호", "prediction").dropDuplicates()

# 조인
joined_df = df_member_unique.join(
    df_customer_unique, on="발급회원번호", how="inner"
)

# cluster와 prediction이 서로 다른 경우만 필터링
filtered_df = joined_df.filter(joined_df["cluster"] != joined_df["prediction"])

# 결과 확인
display(filtered_df.limit(10))

# COMMAND ----------

df_1_fina_billing = spark.read.format("delta").load("dbfs:/user/hive/warehouse/database_pjt.db/1_fina_billing")

df_1_fina_card_history = spark.read.format("delta").load("dbfs:/user/hive/warehouse/database_pjt.db/1_fina_card_history")

df_1_fina_card_usage = spark.read.format("delta").load("dbfs:/user/hive/warehouse/database_pjt.db/1_fina_card_usage")

df_1_fina_entire = spark.read.format("delta").load("dbfs:/user/hive/warehouse/database_pjt.db/1_fina_entire")

df_1_fina_log = spark.read.format("delta").load("dbfs:/user/hive/warehouse/database_pjt.db/1_fina_log")

df_1_fina_marketing_consent = spark.read.format("delta").load("dbfs:/user/hive/warehouse/database_pjt.db/1_fina_marketing_consent")

df_1_fina_member = spark.read.format("delta").load("dbfs:/user/hive/warehouse/database_pjt.db/1_fina_member")

df_3_amount_nonperiod = spark.read.format("delta").load("dbfs:/user/hive/warehouse/database_pjt.db/3_amount_nonperiod")

df_3_amount_period = spark.read.format("delta").load("dbfs:/user/hive/warehouse/database_pjt.db/3_amount_period")

df_3_count_nonperiod = spark.read.format("delta").load("dbfs:/user/hive/warehouse/database_pjt.db/3_count_nonperiod")

df_3_count_period = spark.read.format("delta").load("dbfs:/user/hive/warehouse/database_pjt.db/3_count_period")

df_3_date = spark.read.format("delta").load("dbfs:/user/hive/warehouse/database_pjt.db/3_date")

df_3_other_nonperiod = spark.read.format("delta").load("dbfs:/user/hive/warehouse/database_pjt.db/3_other_nonperiod")

df_3_other_period = spark.read.format("delta").load("dbfs:/user/hive/warehouse/database_pjt.db/3_other_period")

df_3_use_after_month = spark.read.format("delta").load("dbfs:/user/hive/warehouse/database_pjt.db/3_use_after_month")

df_3_use_encoding = spark.read.format("delta").load("dbfs:/user/hive/warehouse/database_pjt.db/3_use_encoding")

df_3_use_encoding_clustered = spark.read.format("delta").load("dbfs:/user/hive/warehouse/database_pjt.db/3_use_encoding_clustered")

df_3_use_encoding_full_clusteredt = spark.read.format("delta").load("dbfs:/user/hive/warehouse/database_pjt.db/3_use_encoding_full_clustered")

df_3_use_encoding_sample = spark.read.format("delta").load("dbfs:/user/hive/warehouse/database_pjt.db/3_use_encoding_sample")

df_3_use_month = spark.read.format("delta").load("dbfs:/user/hive/warehouse/database_pjt.db/3_use_month")

# COMMAND ----------

display(df_1_fina_billing.limit(3))

# COMMAND ----------

display(df_1_fina_card_history.limit(3))

# COMMAND ----------

display(df_1_fina_card_usage.limit(3))

# COMMAND ----------

display(df_1_fina_entire.limit(3))

# COMMAND ----------

display(df_1_fina_log.limit(3))

# COMMAND ----------

display(df_1_fina_marketing_consent.limit(3))

# COMMAND ----------

display(df_1_fina_member.limit(3))

# COMMAND ----------

display(df_3_amount_nonperiod.limit(3))

# COMMAND ----------

display(df_3_amount_period.limit(3))

# COMMAND ----------

display(df_3_count_nonperiod.limit(3))

# COMMAND ----------

display(df_3_count_period.limit(3))

# COMMAND ----------

display(df_3_date.limit(3))

# COMMAND ----------

display(df_3_other_nonperiod.limit(3))

# COMMAND ----------

display(df_3_other_period.limit(3))

# COMMAND ----------

display(df_3_use_after_month.limit(3))

# COMMAND ----------

display(df_3_use_encoding.limit(3))

# COMMAND ----------

display(df_3_use_encoding_clustered.limit(3))

# COMMAND ----------

display(df_3_use_encoding_full_clusteredt.limit(3))

# COMMAND ----------

display(df_3_use_encoding_sample.limit(3))

# COMMAND ----------

display(df_3_use_month.limit(3))