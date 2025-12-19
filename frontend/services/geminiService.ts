import { GoogleGenAI, GenerateContentResponse } from "@google/genai";
import { ChatMessage, SourceCitation } from "../types";

const API_KEY = process.env.API_KEY || '';

const ai = API_KEY ? new GoogleGenAI({ apiKey: API_KEY }) : null;

export const sendMessageToVeri = async (
  history: ChatMessage[], 
  newMessage: string
): Promise<ChatMessage> => {
  
  // Mock response if no API key is present
  if (!ai) {
    console.warn("No API_KEY found. Returning mock response.");
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          id: crypto.randomUUID(),
          role: 'assistant',
          content: "Soy Veri, tu asistente de IA. Puedo buscar en documentos y ayudarte a gestionar los datos de tu organización. Para usar mis capacidades completas, configura la `API_KEY`.",
          timestamp: new Date().toISOString(),
          request_id: `req_${Math.random().toString(36).substr(2, 9)}`,
          sources: [
            {
              type: 'document',
              id: 'doc-mock-1',
              title: 'Guia_Inicio_Rapido.pdf',
              snippet: 'Verity te permite chatear con tus documentos de forma segura y eficiente...',
              relevance: 0.99
            }
          ]
        });
      }, 1000);
    });
  }

  try {
    const chat = ai.chats.create({
      model: 'gemini-2.5-flash',
      config: {
        systemInstruction: "Eres Veri, un asistente inteligente para una plataforma de gestión documental. Tu objetivo es ayudar a los usuarios a encontrar información en sus documentos, proponer cambios en los datos y proporcionar resúmenes. Siempre cita tus fuentes. Responde en español.",
        temperature: 0.7,
      },
    });

    const result: GenerateContentResponse = await chat.sendMessage({
      message: newMessage
    });
    
    // Simulating source extraction
    const mockSources: SourceCitation[] = [
        {
            type: 'document',
            id: 'doc-real-1',
            title: 'Contexto_Subido.pdf',
            snippet: 'Esta es una cita simulada basada en el contexto de la respuesta generada.',
            relevance: 0.85
        }
    ];

    return {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: result.text || "Procesé la solicitud pero no pude generar una respuesta de texto.",
      timestamp: new Date().toISOString(),
      request_id: `req_${Math.random().toString(36).substr(2, 9)}`,
      sources: mockSources
    };

  } catch (error) {
    console.error("Error communicating with Veri:", error);
    return {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: "Encontré un error al procesar tu solicitud. Por favor intenta de nuevo más tarde.",
      timestamp: new Date().toISOString()
    };
  }
};