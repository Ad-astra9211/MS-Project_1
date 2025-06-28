kubectl apply -f k8s/temp-postgres-migration.yaml
kubectl wait --for=condition=Ready pod/postgres-migration-pod -n pr1sm --timeout=60s
kubectl cp postgres_data postgres-migration-pod:/var/lib/postgresql/data/pgdata -n pr1sm
kubectl exec -it postgres-migration-pod -n pr1sm -- sh -c "
echo '=== 복사 완료 후 상태 확인 ==='
ls -la /var/lib/postgresql/data/

echo '=== pgdata 내용 확인 ==='
ls -la /var/lib/postgresql/data/pgdata/ | head -10

echo '=== 권한 수정 (PostgreSQL용) ==='
chown -R 70:70 /var/lib/postgresql/data/pgdata
chmod -R 700 /var/lib/postgresql/data/pgdata

echo '=== 권한 수정 완료 ==='
ls -la /var/lib/postgresql/data/pgdata/ | head -5
"
kubectl delete pod postgres-migration-pod -n pr1sm
kubectl scale statefulset postgres --replicas=1 -n pr1sm