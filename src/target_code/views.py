from fastapi import APIRouter, Depends, HTTPException
from src.database.core import get_db
from src.repo.service import get as get_repo
from src.auth.service import get_current_user

from src.test_modules.service import get_tm_by_name

from .models import TgtCodeDeleteRequest
from .service import delete_target_code


tgtcode_router = APIRouter()


@tgtcode_router.post("/tgt_code/delete/")
async def delete_tgt_code(
    tgt_delete_req: TgtCodeDeleteRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Delete all target code for a tesst module
    """
    try:
        repo = get_repo(
            db_session=db, curr_user=user, repo_name=tgt_delete_req.repo_name
        )
        print(repo.id)
        tm_model = get_tm_by_name(
            db_session=db, repo_id=repo.id, tm_name=tgt_delete_req.tm_name
        )
        print(tm_model.id)
        deleted = delete_target_code(db_session=db, tm_id=tm_model.id)
        print("Deleted: ", deleted)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"detail": "Target code deleted"}
