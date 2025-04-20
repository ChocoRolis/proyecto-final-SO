# Guía para contribuir código a este repositorio

este documento describe el flujo de trabajo que se recomienda para subir código a un repositorio de github. El objetivo es mantener el código organizado y evitar conflictos.

## Flujo de Trabajo

1.  **Haz un Fork del Repositorio:**
    Si aún no lo has hecho, ve a la página principal del repo y haz clic en el botón "Fork". Esto creará una copia del repositorio en tu cuenta.

2.  **Clona Tu Fork Localmente:**
    Asegura que tengas **git** instalado. Abre una terminal y clona *tu* fork (no el del repositorio original):
    ```bash
    git clone <URL_DE_TU_FORK>
    cd <NOMBRE_DEL_REPOSITORIO>
    ```

3.  **Configura el Upstream (Opcional pero Recomendado):**
    Añade el repositorio original como "upstream". Esto te permitirá sincronizar tu fork con los cambios que se hagan en el repositorio principal.
    ```bash
    git remote add upstream https://github.com/ChocoRolis/proyecto-final-SO.git
    ```
    Puedes verificar tus remotos con `git remote -v`. Deberías ver `origin` (tu fork) y `upstream` (el repo original).

4.  **Sincroniza Tu Fork (Frecuentemente):**
    Antes de empezar a trabajar en una nueva funcionalidad o arreglo, es CRUCIAL que sincronices tu fork con el repositorio original para asegurarte de que estás trabajando con la última versión.
    ```bash
    git checkout main # O la rama principal (master)
    git pull upstream main # Descarga los cambios del repo original
    git push origin main # Sube los cambios a tu fork
    ```

5.  **Crea una Nueva Rama para Tus Cambios:**
    SIEMPRE trabaja en una rama separada para cada funcionalidad o arreglo. Esto mantiene tus cambios aislados y facilita la gestión de *pull requests*. Elige un nombre descriptivo para tu rama (ej. `feature/add-sjf-scheduler`, `fix/csv-writing`).
    ```bash
    git checkout -b <NOMBRE_DE_TU_RAMA>
    ```

6.  **Realiza Tus Cambios:**
    Escribe tu código, implementa la funcionalidad, arregla el bug, etc. Revisa el archivo [`TODO.md`](TODO.md) para ver las tareas pendientes.

7.  **Haz Commits de Tus Cambios:**
    Guarda tus cambios localmente (describe los cambios).
    ```bash
    git add . # O git add <archivos específicos>
    git commit -m "implementé el algoritmo Round-Robin"
    ```
    Consulta el archivo [`TODO.md`](TODO.md) para ver las tareas pendientes.

8.  **Empuja Tu Rama a Tu Fork:**
    Una vez que estés listo o quieras guardar tu progreso remotamente, empuja tu nueva rama a *tu* fork:
    ```bash
    git push origin <NOMBRE_DE_TU_RAMA>
    ```

9.  **Crea un Pull Request (PR):**
    Ve a la página principal de *tu* fork en GitHub/GitLab/etc. Verás un banner sugiriendo crear un Pull Request desde tu rama. Haz clic en él o navega a la sección "Pull Requests" y crea uno nuevo.
    *   Asegúrate de que el PR vaya de `<TU_FORK>/<NOMBRE_DE_TU_RAMA>` a `proyecto-final-SO/main`.
    *   Referencia cualquier tarea relevante en el [`TODO.md`](TODO.md). 

10. **Revisión y Fusión:**
    @ChocoRolis revisará el Pull Request. Una vez que el PR sea aprobado, será fusionado en la rama principal del repositorio original.

11. **Limpia (Opcional pero Recomendado):**
    Después de que tu PR sea fusionado, puedes eliminar la rama local y remota que creaste (en tu fork) ya que los cambios ya están en `main`.
    ```bash
    git checkout main # Vuelve a la rama principal
    git branch -d <NOMBRE_DE_TU_RAMA> # Elimina la rama local
    git push origin --delete <NOMBRE_DE_TU_RAMA> # Elimina la rama remota en tu fork
    ```
