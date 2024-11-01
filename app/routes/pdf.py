from fastapi import APIRouter, UploadFile, File, HTTPException
import PyPDF2
router = APIRouter()

@router.post("/upload/")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        reader = PyPDF2.PdfReader(file.file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        # Procesar el texto para extraer preguntas y respuestas
        return {"message": "PDF procesado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al procesar el PDF: {str(e)}")
