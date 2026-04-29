from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import shutil
import os
from pathlib import Path
import tempfile

# Use Hybrid ADT+AST inference (lazy import to avoid crash if models/ missing)
try:
    from models.ast.inference_hybrid import HybridDrumInference
    AST_AVAILABLE = True
except ImportError:
    AST_AVAILABLE = False

router = APIRouter(prefix="/transcription")

# Global inference instance (Lazy load)
_hybrid_inference = None

def get_hybrid_inference():
    global _hybrid_inference
    if not AST_AVAILABLE:
        raise HTTPException(status_code=503, detail="AST model not available")
    if _hybrid_inference is None:
        model_path = Path("models/ast/checkpoints/best_model.pth")
        if not model_path.exists():
            raise RuntimeError("AST Model checkpoint not found!")
        print("Loading Hybrid ADT+AST Model...")
        _hybrid_inference = HybridDrumInference(model_path)
    return _hybrid_inference

@router.post("/ast")
async def transcribe_ast(file: UploadFile = File(...)):
    """
    Transcribe drums using Hybrid ADT Onset + AST Classification.
    Returns JSON compatible with visualization.
    """
    try:
        # Save temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
            
        # Inference
        try:
            inference = get_hybrid_inference()
            result_dict = inference.process_audio(tmp_path)
        except Exception as e:
            # Clean up on error
            os.unlink(tmp_path)
            raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")
            
        # Clean up
        os.unlink(tmp_path)
        
        # Format for UI
        response_data = {
            "bpm": result_dict['bpm'],
            "total_hits": len(result_dict['events']),
            "hits": result_dict['events'],
            "downbeats": result_dict['downbeats']
        }
        
        return JSONResponse(content={
            "transcription": response_data,
            "method": "hybrid_adt_ast"
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))