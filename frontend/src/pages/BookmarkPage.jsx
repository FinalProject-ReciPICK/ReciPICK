import Header from "../components/Header";
import Footer from "../components/Footer";
import api from "../utils/api";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

export default function BookmarkPage() {
  const [recipes, setRecipes] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();
  const userId = localStorage.getItem("userId");

  const fetchBookmarkedRecipes = async () => {
    try {
      setIsLoading(true);
      const res = await api.get("/bookmark/", {
        params: { user_id: userId },
      });
      const ids = res.data.recipe_ids;
      const recipePromises = ids.map((id) =>
        api.get(`/recipe/${id}`).then((r) => r.data)
      );
      const recipeResults = await Promise.all(recipePromises);
      setRecipes(recipeResults);
    } catch (err) {
      //console.error("찜한 레시피 불러오기 실패:", err);
      setRecipes([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemoveBookmark = async (recipeId, e) => {
    e.stopPropagation(); // 카드 클릭 이벤트 방지
    try {
      await api.delete(`/bookmark/${recipeId}`, {
        params: { user_id: userId }
      });
      // 로컬 상태에서 해당 레시피 제거
      setRecipes(prevRecipes => prevRecipes.filter(recipe => recipe.id !== recipeId));
    } catch (err) {
      console.error("북마크 삭제 실패:", err);
      alert("북마크 삭제에 실패했습니다.");
    }
  };

  useEffect(() => {
    if (!userId) {
      navigate("/login", { replace: true });
      return;
    }
    fetchBookmarkedRecipes();
  }, [userId, navigate]);

  return (
    <div className="flex flex-col min-h-screen">
      <main className="flex-grow bg-[#F7F8FA] pb-20">
        <div className="w-full max-w-md mx-auto text-sm">
          <Header title="찜한 레시피" showBack onBack={() => navigate(-1)} />
          <div className="p-4 flex flex-col gap-3">
            {isLoading ? (
              // 로딩 상태
              <div className="flex flex-col items-center justify-center py-16">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#FDA177] mb-4"></div>
                <p className="text-gray-500 text-sm">찜한 레시피를 불러오고 있어요...</p>
              </div>
            ) : recipes.length > 0 ? (
              recipes.map((recipe) => (
                <div
                  key={recipe.id}
                  className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm hover:shadow-md transition cursor-pointer flex items-center relative"
                  onClick={() => navigate(`/recipe/${recipe.id}`)}
                >
                  <img
                    src={recipe.image_url}
                    alt={recipe.title}
                    className="w-20 h-20 object-cover flex-shrink-0 ml-2 my-2 rounded-lg"
                  />
                  <div className="flex flex-col justify-center flex-1 px-3 py-2 pr-8">
                    <div className="text-sm font-normal text-gray-800">{recipe.title}</div>
                  </div>
                  <button
                    onClick={(e) => handleRemoveBookmark(recipe.id, e)}
                    className="absolute top-1 right-1 w-6 h-6 text-gray-400 hover:text-red-500 flex items-center justify-center text-lg font-normal transition-colors"
                    title="북마크 삭제"
                  >
                    ×
                  </button>
                </div>
              ))
            ) : (
              // 찜한 레시피가 없을 때 안내 UI
              <div className="flex flex-col items-center justify-center py-16 px-4">
                <div className="text-6xl mb-4">💔</div>
                <h3 className="text-lg font-semibold text-gray-800 mb-2">
                  찜한 레시피가 없어요
                </h3>
                <p className="text-sm text-gray-500 text-center mb-6 leading-relaxed">
                  마음에 드는 레시피를 찾아서<br />
                  하트 버튼을 눌러 저장해보세요!
                </p>
                <button
                  onClick={() => navigate('/')}
                  className="bg-[#FDA177] text-white px-6 py-3 rounded-xl font-medium hover:bg-[#fc5305] transition"
                >
                  레시피 둘러보기
                </button>
              </div>
            )}
          </div>
        </div>
      </main>
      <div className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-md z-50">
        <Footer />
      </div>
    </div>
  );
}
