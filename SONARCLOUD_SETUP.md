# Guía de Configuración de SonarCloud para Checkers

## 📋 Pasos para obtener un reporte real de SonarQube

### 1. Crear cuenta en SonarCloud (2 minutos)

1. Ve a: **https://sonarcloud.io**
2. Haz clic en **"Sign up"**
3. Selecciona **"Continue with GitHub"**
4. Autoriza SonarCloud a acceder a tu cuenta de GitHub

### 2. Importar tu repositorio (3 minutos)

1. Una vez logueado, haz clic en el **"+"** (arriba derecha) → **"Analyze new project"**
2. Selecciona la organización **"Gustavo-Eduardo"** (tu usuario de GitHub)
3. Si no aparece, necesitas:
   - Ir a https://github.com/settings/installations
   - Buscar "SonarCloud"
   - Dar acceso al repositorio **"checkers"**
4. Vuelve a SonarCloud y selecciona el repositorio **"checkers"**
5. Haz clic en **"Set Up"**

### 3. Configurar el proyecto (2 minutos)

1. En la página de configuración del proyecto:
   - **Analysis Method:** Selecciona **"With GitHub Actions"**
   - SonarCloud te mostrará instrucciones

2. **Crear el Secret en GitHub:**
   - Ve a tu repositorio: https://github.com/Gustavo-Eduardo/checkers
   - Ve a **Settings** → **Secrets and variables** → **Actions**
   - Haz clic en **"New repository secret"**
   - Name: `SONAR_TOKEN`
   - Value: (copia el token que SonarCloud te muestra)
   - Haz clic en **"Add secret"**

### 4. Verificar archivos del proyecto

Ya creé estos archivos automáticamente:

✅ `.github/workflows/sonarcloud.yml` - GitHub Action para análisis automático
✅ `sonar-project.properties` - Configuración actualizada para SonarCloud

### 5. Ejecutar el primer análisis

**Opción A: Push a GitHub (automático)**
```powershell
# Desde la raíz del proyecto
git add .
git commit -m "Add SonarCloud configuration"
git push origin main
```

Luego:
- Ve a: https://github.com/Gustavo-Eduardo/checkers/actions
- Verás el workflow "SonarCloud Analysis" ejecutándose
- Espera 2-3 minutos a que termine

**Opción B: Análisis local manual**

Si prefieres ejecutar el análisis desde tu máquina:

```powershell
# 1. Descargar SonarScanner CLI
# Ir a: https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/
# Descargar: sonar-scanner-cli-5.0.1.3006-windows.zip
# Descomprimir en C:\sonar-scanner

# 2. Agregar a PATH (temporal, solo esta sesión)
$env:Path += ";C:\sonar-scanner\bin"

# 3. Ejecutar análisis
cd C:\Users\USUARIO\Documents\GitHub\checkers

sonar-scanner `
  -Dsonar.organization=gustavo-eduardo `
  -Dsonar.projectKey=Gustavo-Eduardo_checkers `
  -Dsonar.sources=. `
  -Dsonar.host.url=https://sonarcloud.io `
  -Dsonar.login=<PEGA_TU_TOKEN_AQUI>
```

### 6. Ver el reporte real

1. Ve a: **https://sonarcloud.io/project/overview?id=Gustavo-Eduardo_checkers**
2. O desde tu dashboard de SonarCloud, haz clic en el proyecto **"checkers"**

Verás:
- 📊 **Overview:** Resumen de bugs, vulnerabilidades, code smells
- 🐛 **Issues:** Lista detallada de todos los problemas
- 📈 **Measures:** Métricas de complejidad, duplicaciones, tamaño
- 🔒 **Security:** Security hotspots y vulnerabilidades
- 📉 **Code:** Explorador de código con problemas marcados
- ⏱️ **Activity:** Historial de análisis

---

## 🎯 Qué esperar en el primer reporte

Basado en el análisis local, tu reporte real mostrará aproximadamente:

- **Bugs:** ~7-8
- **Vulnerabilities:** 0
- **Code Smells:** ~50-60
- **Security Hotspots:** 0
- **Coverage:** 0% (hasta que agregues tests)
- **Duplications:** ~1.5-2%
- **Technical Debt:** ~5-6 horas

**Quality Gate:** Probablemente FAILED (por falta de cobertura y complejidad alta)

---

## 🔄 Análisis automático en cada commit

Una vez configurado, SonarCloud analizará automáticamente:
- ✅ Cada push a la rama `main`
- ✅ Cada Pull Request
- ✅ Comentará en los PRs con los issues encontrados

---

## 🛠️ Próximos pasos después del primer análisis

1. **Revisar el reporte** en SonarCloud
2. **Configurar Quality Gate** (opcional, para establecer estándares mínimos)
3. **Agregar badge** al README:
   ```markdown
   [![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=Gustavo-Eduardo_checkers&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=Gustavo-Eduardo_checkers)
   ```
4. **Comenzar a resolver** los issues críticos

---

## ❓ Troubleshooting

**Si el workflow falla:**
- Verifica que el `SONAR_TOKEN` esté configurado correctamente
- Revisa los logs en GitHub Actions
- Asegúrate de que la organización sea `gustavo-eduardo` (tu username en minúsculas)

**Si el análisis local falla:**
- Verifica que Java 17+ esté instalado: `java -version`
- Verifica que el token sea correcto
- Revisa que `sonar-scanner` esté en PATH

**Para soporte:**
- Documentación: https://docs.sonarcloud.io/
- Community: https://community.sonarsource.com/

---

## 📝 Notas importantes

- SonarCloud es **gratis para proyectos públicos** en GitHub
- El análisis corre en servidores de SonarSource (no consume recursos locales)
- Los reportes se mantienen online y puedes comparar con análisis anteriores
- Puedes integrar con PRs para bloquear merges que no cumplan Quality Gate

---

**¿Listo para comenzar?** Sigue los pasos 1-5 y tendrás tu reporte real en ~10 minutos.
