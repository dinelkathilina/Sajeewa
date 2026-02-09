import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  DollarSign,
  Clock,
  CheckCircle,
  Download,
  ArrowLeft,
  Edit2,
  Save,
  X,
  AlertCircle,
} from "lucide-react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import {
  getVariation,
  updateVariationDetail,
  updateVariationStatus,
  generatePDF,
} from "../services/api";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
);

const ProposalPage = () => {
  const { variationId } = useParams<{ variationId: string }>();
  const navigate = useNavigate();

  const [variation, setVariation] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingDetailId, setEditingDetailId] = useState<number | null>(null);
  const [editValues, setEditValues] = useState<any>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (variationId) {
      loadVariation();
    }
  }, [variationId]);

  const loadVariation = async () => {
    try {
      setLoading(true);
      const data = await getVariation(Number(variationId));
      setVariation(data);
    } catch (err: any) {
      setError("Failed to load variation details");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const startEdit = (detail: any) => {
    setEditingDetailId(detail.id);
    setEditValues({
      new_rate: detail.new_rate,
      new_quantity: detail.new_quantity,
      new_description: detail.new_description || detail.original_description,
      justification: detail.justification || "",
    });
  };

  const cancelEdit = () => {
    setEditingDetailId(null);
    setEditValues({});
  };

  const saveEdit = async (detailId: number) => {
    try {
      setSaving(true);
      await updateVariationDetail(Number(variationId), detailId, editValues);
      setEditingDetailId(null);
      await loadVariation(); // Reload to get updated totals
    } catch (err) {
      setError("Failed to save changes");
    } finally {
      setSaving(false);
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    try {
      setSaving(true);
      await updateVariationStatus(Number(variationId), newStatus);
      await loadVariation();
    } catch (err) {
      setError("Failed to update status");
    } finally {
      setSaving(false);
    }
  };

  const handleDownloadPDF = async () => {
    try {
      const blob = await generatePDF({ variation_id: Number(variationId) });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `Variation_Proposal_${variationId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      setError("Failed to generate PDF");
    }
  };

  if (loading)
    return <div className="p-8 text-center">Loading variation details...</div>;
  if (!variation)
    return (
      <div className="p-8 text-center text-red-600">Variation not found.</div>
    );

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 pb-12">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate(-1)}
                className="text-gray-600 hover:text-gray-900"
              >
                <ArrowLeft className="w-6 h-6" />
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  Variation Proposal
                </h1>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-600">
                    Ref: #{variation.id}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-semibold ${
                      variation.status === "Approved"
                        ? "bg-green-100 text-green-800"
                        : variation.status === "Rejected"
                          ? "bg-red-100 text-red-800"
                          : "bg-yellow-100 text-yellow-800"
                    }`}
                  >
                    {variation.status}
                  </span>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              {variation.status !== "Approved" && (
                <button
                  onClick={() => handleStatusChange("Approved")}
                  className="btn-primary bg-green-600 hover:bg-green-700 flex items-center space-x-2"
                >
                  <CheckCircle className="w-4 h-4" />
                  <span>Approve</span>
                </button>
              )}
              <button
                onClick={handleDownloadPDF}
                className="btn-secondary flex items-center space-x-2"
              >
                <Download className="w-5 h-5" />
                <span>Download PDF</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg flex items-center space-x-2">
            <AlertCircle className="w-5 h-5" />
            <span>{error}</span>
          </div>
        )}

        {/* Executive Summary */}
        <div className="card">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            Executive Summary
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-blue-50 rounded-lg p-6">
              <div className="flex items-center space-x-3 mb-2">
                <DollarSign className="w-8 h-8 text-blue-600" />
                <h3 className="text-sm font-medium text-gray-600">
                  Cost Impact
                </h3>
              </div>
              <p className="text-3xl font-bold text-blue-600">
                $
                {variation.cost_impact?.toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                }) || "0.00"}
              </p>
            </div>

            <div className="bg-emerald-50 rounded-lg p-6">
              <div className="flex items-center space-x-3 mb-2">
                <Clock className="w-8 h-8 text-emerald-600" />
                <h3 className="text-sm font-medium text-gray-600">
                  Time Impact
                </h3>
              </div>
              <p className="text-3xl font-bold text-emerald-600">
                {variation.time_impact || 0} days
              </p>
            </div>

            <div className="bg-gray-50 rounded-lg p-6">
              <h3 className="text-sm font-medium text-gray-600 mb-2">
                Description
              </h3>
              <p className="text-gray-800 text-sm">{variation.description}</p>
            </div>
          </div>
        </div>

        {/* Cost Breakdown (Editable) */}
        <div className="card overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-900">Cost Breakdown</h2>
            <span className="text-sm text-gray-500 italic">
              Click pencil icon to edit line items
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/3">
                    Item Description
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Orig Qty
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    New Qty
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    New Rate
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Impact
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {variation.details &&
                  variation.details.map((detail: any) => (
                    <tr
                      key={detail.id}
                      className={
                        editingDetailId === detail.id ? "bg-blue-50" : ""
                      }
                    >
                      {editingDetailId === detail.id ? (
                        // Edit Mode
                        <>
                          <td className="px-6 py-4">
                            <input
                              type="text"
                              className="input-field text-sm"
                              value={editValues.new_description}
                              onChange={(e) =>
                                setEditValues({
                                  ...editValues,
                                  new_description: e.target.value,
                                })
                              }
                            />
                            <input
                              type="text"
                              placeholder="Justification"
                              className="input-field text-xs mt-1"
                              value={editValues.justification}
                              onChange={(e) =>
                                setEditValues({
                                  ...editValues,
                                  justification: e.target.value,
                                })
                              }
                            />
                          </td>
                          <td className="px-4 py-4 text-right text-sm text-gray-500">
                            {detail.original_quantity}
                          </td>
                          <td className="px-4 py-4">
                            <input
                              type="number"
                              className="input-field text-right text-sm w-24"
                              value={editValues.new_quantity}
                              onChange={(e) =>
                                setEditValues({
                                  ...editValues,
                                  new_quantity: Number(e.target.value),
                                })
                              }
                            />
                          </td>
                          <td className="px-4 py-4">
                            <input
                              type="number"
                              className="input-field text-right text-sm w-28"
                              value={editValues.new_rate}
                              onChange={(e) =>
                                setEditValues({
                                  ...editValues,
                                  new_rate: Number(e.target.value),
                                })
                              }
                            />
                          </td>
                          <td className="px-4 py-4 text-right text-sm font-medium text-gray-900">
                            -
                          </td>
                          <td className="px-4 py-4 text-right">
                            <div className="flex justify-end space-x-2">
                              <button
                                onClick={() => saveEdit(detail.id)}
                                disabled={saving}
                                className="text-green-600 hover:text-green-800"
                              >
                                <Save className="w-5 h-5" />
                              </button>
                              <button
                                onClick={cancelEdit}
                                className="text-gray-500 hover:text-gray-700"
                              >
                                <X className="w-5 h-5" />
                              </button>
                            </div>
                          </td>
                        </>
                      ) : (
                        // View Mode
                        <>
                          <td className="px-6 py-4">
                            <div className="text-sm font-medium text-gray-900">
                              {detail.new_description ||
                                detail.original_description}
                            </div>
                            <div className="text-xs text-gray-500">
                              Src: {detail.rate_source || "Original"}
                            </div>
                            {detail.justification && (
                              <div className="text-xs text-amber-600 mt-1 italic">
                                "{detail.justification}"
                              </div>
                            )}
                          </td>
                          <td className="px-4 py-4 text-right text-sm text-gray-500">
                            {detail.original_quantity}
                          </td>
                          <td className="px-4 py-4 text-right text-sm text-gray-900 font-medium">
                            {detail.new_quantity}
                          </td>
                          <td className="px-4 py-4 text-right text-sm text-gray-900">
                            {detail.new_rate?.toLocaleString()}
                          </td>
                          <td
                            className={`px-4 py-4 text-right text-sm font-bold ${detail.cost_impact >= 0 ? "text-green-600" : "text-red-600"}`}
                          >
                            {detail.cost_impact > 0 ? "+" : ""}
                            {detail.cost_impact?.toLocaleString()}
                          </td>
                          <td className="px-4 py-4 text-right">
                            {variation.status !== "Approved" && (
                              <button
                                onClick={() => startEdit(detail)}
                                className="text-blue-600 hover:text-blue-800"
                              >
                                <Edit2 className="w-4 h-4" />
                              </button>
                            )}
                          </td>
                        </>
                      )}
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProposalPage;
