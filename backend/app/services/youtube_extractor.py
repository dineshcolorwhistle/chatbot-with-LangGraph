import re
import os
import logging
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from fpdf import FPDF

logger = logging.getLogger(__name__)

class YouTubeExtractorService:
    """
    Service to extract subtitles/transcripts from YouTube videos,
    format them, and save them as PDF documents.
    """

    @classmethod
    def _extract_video_id(cls, url: str) -> str:
        """
        Parse YouTube URL and extract the video ID.
        Supports standard, embed, and shortened URLs.
        """
        parsed_url = urlparse(url)
        
        # 1. Shortened format: youtu.be/VIDEO_ID
        if parsed_url.netloc == "youtu.be":
            return parsed_url.path.lstrip("/")
            
        # 2. Embed format: youtube.com/embed/VIDEO_ID
        if "embed" in parsed_url.path:
            return parsed_url.path.split("/")[-1]
            
        # 3. Standard format: youtube.com/watch?v=VIDEO_ID
        if parsed_url.netloc in ("www.youtube.com", "youtube.com"):
            query_params = parse_qs(parsed_url.query)
            video_ids = query_params.get("v")
            if video_ids:
                return video_ids[0]
                
        # Fallback regex search
        match = re.search(r"(?:v=|\/)([\w-]{11})(?:\?|&|$)", url)
        if match:
            return match.group(1)
            
        raise ValueError(f"Could not extract YouTube video ID from URL: {url}")

    @classmethod
    async def extract_and_save_as_pdf(cls, video_url: str, output_folder: str) -> str:
        """
        Download YouTube transcript, convert it to a clean PDF,
        and return the generated PDF file path.
        """
        # 1. Parse video ID
        video_id = cls._extract_video_id(video_url)
        logger.info(f"🎥 Fetching transcript for YouTube video ID: {video_id}")

        # 2. Retrieve transcript from YouTube API
        try:
            # First try retrieving english transcript
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
        except Exception as e_en:
            logger.warning(f"Could not retrieve English transcript directly: {e_en}. Attempting default fallback.")
            try:
                # Fallback to whatever language is available
                list_transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
                transcript = list_transcripts.find_transcript(["en"])
                transcript_list = transcript.fetch()
            except Exception as e_fallback:
                logger.error(f"❌ Failed to retrieve YouTube transcript: {e_fallback}")
                raise ValueError(f"YouTube transcript is disabled or not available: {str(e_fallback)}")

        # 3. Join transcript blocks into raw paragraph text
        text_blocks = []
        for block in transcript_list:
            text_blocks.append(block.get("text", "").strip())
        
        full_transcript_text = " ".join(text_blocks).replace("\n", " ").strip()
        
        if not full_transcript_text:
            raise ValueError("Retrieved transcript is empty.")

        # 4. Generate PDF using fpdf2
        logger.info("📄 Generating PDF from transcript text...")
        pdf_filename = f"youtube_transcript_{video_id}.pdf"
        pdf_path = os.path.join(output_folder, pdf_filename)
        
        try:
            pdf = FPDF()
            pdf.add_page()
            
            # Use core Helvetica font (standard in FPDF, no external file needed)
            pdf.set_font("Helvetica", size=12)
            
            # Document Title Header
            pdf.set_font("Helvetica", style="B", size=16)
            pdf.cell(w=0, h=10, txt="YouTube Video Transcript Ingestion", ln=1, align="C")
            pdf.set_font("Helvetica", style="I", size=10)
            pdf.cell(w=0, h=10, txt=f"Source URL: {video_url}", ln=1, align="C")
            pdf.ln(5)
            
            # Subtitle body text
            pdf.set_font("Helvetica", size=11)
            
            # Sanitize text for standard PDF encoding (latin-1) to avoid character encoding crashes
            safe_text = full_transcript_text.encode("latin-1", errors="replace").decode("latin-1")
            
            # Print body text using multi_cell for line wrapping
            pdf.multi_cell(w=0, h=6, txt=safe_text)
            
            # Save PDF file
            pdf.output(pdf_path)
            logger.info(f"📄 Successfully created PDF file: {pdf_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to construct PDF: {e}")
            raise RuntimeError(f"Failed to generate PDF document structure: {e}")

        return pdf_path
