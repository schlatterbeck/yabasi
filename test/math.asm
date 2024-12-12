; Swith section to data
jmp DOIT
;.bss
ARG:   .word 0x0
DPADR: .word 0x0
FAC:   .word 0x0
FACLO: .word 0x0
VALTP: .word 0x4 ; single precision seems to be 0x4 aka 'LOW 4'
;.endseg

;***********************************************************
;
;       $OVFLS  PLACES CORRECT INFINITY IN THE FAC AND PRINTS
;               OVERFLOW MESSAGE
;
;       $DIV0S  PLACES CORRECT INFINITY IN THE FAC AND PRINTS
;               DIVIDE-BY-ZERO MESSAGE
;
;***********************************************************

; we don't care about overflows

$OVFLS: PUSH	BX
	CALL	OVFLS		;DO THE OVERFLOW CODE
	POP	BX		;RESTORE TEXT POINTER
	RET
OVFLS:	HLT

;
; Set cond. codes according to type value.
;   S, C = Integer
;   Z, C = String
;      C = Single Precision
;   None = Double Precision
;
$GETYP:
	MOV	AL,BYTE PTR [VALTP]	;FETCH TYPE VARIABLE
	CMP	AL,0x8	        ;CF=1 EXCEPT FOR DOUBLE PREC.
	DEC	AL		;WILL SUBTRACT 3 WITH DECBREMENTS
	DEC	AL
	DEC	AL
	RET			;ZF=1 IF STRING,SF=1 IF INTEGER
				;PO=1 IF SINGLE PREC

$ZERO:				;ZERO THE FAC
	MOV	AX,0
	MOV	WORD PTR [FACLO],AX	;ZERO LOWER 2 BYTES
	MOV	WORD PTR [FAC-1],AX	;ZERO UPPER TWO BYTES
	RET

SIGN:
$SIGNS:			;DETERMINE SIGN OF FAC
				;ZF=1 IF (FAC)=0, SF=1 IF (FAC) .LT.0, NEITHER OF
				;THESE FLAGS SET IF (FAC).GT.0
	CALL	$GETYP		;IF NOT INTEGER CAN LOOK AT FAC:FAC-1
	JNE	SIS01
	; This changed, we just halt the processor, should never happen
	; that we have mismatched types
	JMP	OVFLS		;Strings illegal 9-Mar-82/ngt
SIS01:
	JNS	SIS05		;NOT INTEGER PROCEED
	MOV	AX,WORD PTR [FACLO]	;FETCH INTEGER
	OR	AX,AX		;DETERMINE SIGN
	JZ	SIS10
	MOV	AL,1
	JNS	SIS10
	NEG	AL
	RET
SIS05:
	MOV	AL,BYTE PTR [FAC]	;FIRST CHECK FOR ZERO
	OR	AL,AL
	JZ	SIS10		;IF ZERO JUST RETURN
	MOV	AL,BYTE PTR [FAC-1]	;FETCH SIGN BYTE
SIGNAL: OR	AL,AL		;SIGNSET NOW
	JZ	SIS07		;MUST MAKE AL=1 AND ZF=0
	MOV	AL,1
	JNS	SIS10
	NEG	AL
	RET
SIS07:	OR	AL,1	;KNOW POSITIVE NON-ZERO
SIS10:	RET

;***********************************************************
;
;       $ROUNS  SINGLE PRECISION ROUNDING SUBROUTINE
;       CALLING SEQUENCE:       CALL    $ROUNS
;       ASSUMPTIONS:    (BLDXAH)WILL BE ROUNDED BY ADDING
;                       128 TO (AH) . IF CF (CARRY) IS SET
;                       AND (AH) IS NON-ZERO AFTER THIS
;                       ADDITION (BLDX) WILL BE INCREMENTED
;                       ONCE ROUNDING IS COMPLETE, LOGIC WILL
;                       CONTINUE INTO PAKSP FOR PACKING THE MANTISSA
;                       AND SIGN INTO THE FAC.
;
;**************************************************************

$ROUNS: AND	AH,0xe0	;CLEAR SUPERFLUOUS BITS
$ROUNM: ADD	AH,0x80	;ADD TO MOST SIG. BIT OF AH
	JNB	PAKSP		;IF NO CARRY RETURN
	PUSHF			;IF ZF=1 WANT TO ROUND TO EVEN
	INC	DX		;IF ZF=1 MUST INCREMENT BL
	JNZ	TSTEVN
	POPF			;KNOW RESULT WILL BE EVEN
	INC	BL		;IF ZF=1 MUST INCREMENT EXPONENT
	JNZ	PAKSP
	STC			;CF=1
	RCR	BL,1		;THIS WILL SET HIGH BIT OF BL
	INC	BYTE PTR [FAC]	;IF THIS CAUSES (FAC)=0 WE HAVE
				;OVERFLOW IN ROUNDING
	JNZ	PAKSP
	JMP	$OVFLS
TSTEVN: POPF			;IF ZF=1 MUST CLEAR LOW BIT OF DL
	JNZ	PAKSP		;GO PACK THE FAC
	AND	DL,0xfe		;CLEAR LOW BIT
PAKSP:				;PAK SINGLE PRECISION FAC. EXPONENT IS IN FAC,SIGN IN FAC+1
				;THE MANTISSA IS IN (BLDX)
	MOV	SI,FAC-3	;LOAD ADDRESS OF FAC IN SI
	MOV	WORD PTR 0[SI],DX	;MOVE LOWER MANTISSA WORD IN
	INC	SI		;INCREMENT TO HIGH MANTISSA BYTE
	INC	SI		;
	MOV	BH,BYTE PTR [FAC+1]	;FETCH SIGN
	AND	BX,0x807f	;CLEAR ALL BUT SIGN IN BH SIGN IN BL
	OR	BL,BH		;(BL) NOW IN CORRECT FORMAT
	MOV	BYTE PTR 0[SI],BL	;PUT INTO FAC-1
	RET

;*************************************************************
;
;       $AEXPS,$SEXPS   WILL PERFORM THE ADDITION/SUBTRACTION
;               OF SINGLE OR DOUBLE PRECISION EXPONENTS.
;       CALLING SEQUENCE:       CALL    $AEXPS
;               OR              CALL    $SEXPS
;               WITH THE SINGLE PRECISION NUMERATOR(MULTIPLIER)
;               IN (BXDX) OR THE DOUBLE PRECISION NUMERATOR
;               (MULTIPLIER) IN (ARG) AND THE DENOMINATOR
;               (MULTIPLICAND) IN THE (FAC)
;               FOR DOUBLE PRECISION OPERATIONS THE ARG  EXPONENT
;               AND HIGH MANTISSA BYTE MUST BE IN BH:BL PRIOR
;               TO A $SEXPS,$AEXPS CALL
;
;**************************************************************


$AEXPS: STC			;CF=1
	JMP	SES00
$SEXPS: CLC			;CF=0
SES00:	MOV	SI,BX		;WILL NEED FOR LATER
	PUSHF			;SAVE MULTIPLY/DIVIDE FLAG
	MOV	CX,WORD PTR [FAC-1]	;(CH)=FAC:(CL)=FAC-1
	MOV	AL,BL		;FETCH (BXDX) SIGN BYTE
	XOR	AL,CL		;CORRECT SIGN IN AL
	MOV	BYTE PTR [FAC+1],AL	;MOVE TO FAC+1
	MOV	AL,BH		;GET (BXDX) EXPONENT
	XOR	AH,AH		;WILL USE 16-BIT ARITHEMETIC
	MOV	BL,CH		;TO CALCULATE EXPONENTS
	XOR	BH,BH
	POPF			;SEE IF ADD OR SUBTRACT OF EXPONENTS
	JNB	SES05		;JUMP IF SUBTRACT
	ADD	AX,BX		;HAVE IN TWO BIASES
	SUB	AX,0x101	;NOW HAVE RAW SUM LESS 1
	JMP	SES07	;GO CHECK FOR OVERFLOW/UNDERFLOW
SES05:	SUB	AX,BX		;BIASES CANCEL OUT
SES07:	OR	AH,AH		;
	JS	SES10		;MUST GO CHECK FOR UNDERFLOW
	CMP	AX,0x80		;CF=0 IF OVERFLOW
	JB	SES20		;PROCEED IF OK
	MOV	BX,SI		;GET (BX) OFF STACK
	ADD	SP,2		;GET $SEXPS RETURN ADDRESS OFF STACK
	JMP	$OVFLS		;GO DO OVERFLOW CODE
SES10:				;POTENTIAL UNDERFLOW
	ADD	AX,0x80		;BIAS MUST BRING IT IN POSITIVE
	JNS	SES30		;IF IT IS POSITIVE PROCEED
	MOV	BX,SI		;BET (BX) OFF STACK
	ADD	SP,2		;GET $SEXPS RETURN ADDRESS OFF STACK
	JMP	$ZERO		;GO ZERO THE FAC AND RETURN
SES20:	ADD	AX,0x80		;ADD IN THE BIAS
SES30:	MOV	BYTE PTR [FAC],AL	;PUT CORRECT EXPONENT IN FAC
	MOV	BX,FAC-1	;ADDRESS OF HIGH MANTISSA BITS
	OR	BYTE PTR 0[BX],0x80	;OR IN THE HIDDEN "1"
	MOV	BX,SI		;GET (BXDX) HIGH MANTISSA BITS
	XOR	BH,BH		;CLEAR SUPERFLUOUS BITS
	OR	BL,0x80		;RESTORE HIDDEN "1"
	RET

;**********************************************************
;       $FMULS  FMULS MULTIPLIES THE SINGLE PRECISION
;               FLOATING POINT QUANTITIES (BXDX) AND (FAC)
;               AND RETURNS THE PRODUCT IN THE (FAC). ONLY
;               SEGMENT REGISTERS ARE PRESERVED.
;***********************************************************

$FMULS:			;(FAC)=(BXDX)*(FAC)
	CALL	$SIGNS		;ZF=1 WILL BE SET IF (FAC)=0
	JZ	FMS00		;JUST RETURN IF (FAC)=0
	OR	BH,BH		;IF EXPONENT OF (BXDX) IS ZERO
	JNZ	FMS05		;PROCEED IF NON-ZERO
FMS00:	JMP	$ZERO		;THE NUMBER IS ZERO.
FMS05:
	CALL	$AEXPS		;ADD THE S.P. EXPONENTS
;***************************************************************
;WILL NOW PROCEED TO MULTIPLY THE MANTISSAS. THE MULTIPLICATION
;WILL UTILIZE THE 16 BIT MUL INSTRUCTION AND THUS WILL TAKE
;PLACE AS PARTIAL PRODUCTS SINCE WE HAVE 24 BIT MANTISSAS TO
;MULTIPLY.
;***************************************************************
	MOV	CX,WORD PTR [FAC-1]	;(CH)=(FAC):(CL)=(FAC-1)
	XOR	CH,CH		;(CX) CONTAINS HIGH MANTISSA BITS
	MOV	AX,WORD PTR [FAC-3]	;(AX) CONTAINS LOW MANTISSA BITS OF FAC
	MOV	BH,CH		;SET (BH)=0 AS WELL
;*************************************************************
;AT THIS POINT WE HAVE THE FAC MANTISSA IN (CLAX) AND THE
;(BXDX) MANTISSA IN (BLDX). THE UNDERSTOOD LEADING MANTISSA
;BIT WAS INSTALLED BY $AEXPS AND THE SIGN OF THE PRODUCT
;WAS STORED IN FAC+1
;THE PRODUCT WILL BE FORMED IN (BXCX) BY PARTIAL PRODUCTS.
;FIRST THE NECESSARY ELEMENTS WILL BE PUSHED ON THE STACK
;THEN UTILIZED IN REVERSE ORDER(THAT'S THE BEST WAY TO
;GET THE THEM OFF THE LIFO STACK -TURKEY!)
;************************************************************
	MOV	SI,BX
	MOV	DI,CX
	MOV	BP,DX
	PUSH	CX		;HIGH FAC MANTISSA BITS
	PUSH	AX		;LOW FAC MANTISSA BITS
	MUL	DX		;32 BIT PRODUCT FORMED(ONLY NEED
	MOV	CX,DX		;MOST 16 SIGNIFICANT BITS)
	POP	AX		;LOW FAC MANTISSA BITS
	MUL	BX		;TIMES HIGH MANTISSA BITS OF (BLDX)
	ADD	CX,AX		;ADD TO PREVIOUS CALCULATION
	JNB	FMS10		;IF CARRY NOT PRODUCED PROCEED
	INC	DX
FMS10:	MOV	BX,DX		;PROBABLY ONLY 8 BITS HERE
	POP	DX		;HIGH FAC MANTISSA BITS
	MOV	AX,BP		;LOW 16 MANTISSA BITS OF (BLDX)
	MUL	DX		;
	ADD	CX,AX		;ADD IN LOW ORDER BITS
	JNB	FMS20		;JUMP IF CARRY NOT PRODUCED
	INC	DX		;
FMS20:	ADD	BX,DX		;CAN'T PRODUCE CARRY HERE
	MOV	DX,DI		;HIGH FAC MANTISSA BITS
	MOV	AX,SI		;HIGH FAC MANTISSA BITS
	MUL	DL		;(AX) HAS ENTIRE PRODUCT
	ADD	BX,AX		;ADD IT IN
	JNB	FMS30		;IF NO CARRY PROCEED
	RCR	BX,1		;MOVE EVERYTHING RIGHT
	RCR	CX,1		;
	INC	BYTE PTR [FAC]	;MUST NOW CHECK FOR OVERFLOW
	JNZ	FMS30		;PROCEED IF NON-ZERO
	JMP	$OVFLS
FMS30:				;PRODUCT FORMED, MUST NOW GET MANTISSA IN (BLDXAH) FOR ROUNS
				;PRODUCT IS CURRENTLY IN (BXCX)
	OR	BH,BH		;MUST BE SURE PRODUCT LEFT JUSTIFIED
	JNS	FMS35		;IN (BXCX)
	INC	BYTE PTR [FAC]	;NEED TO INCREMENT EXP.
	JNZ	FMS37		;IF NOT OVERFLOW PROCEED
	JMP	$OVFLS		;OVERFLOW JUMP
FMS35:
	RCL	CX,1
	RCL	BX,1
FMS37:
	MOV	DL,CH
	MOV	DH,BL
	MOV	BL,BH
	MOV	AH,CL		;OVERFLOW BYTE
	JMP	$ROUNS		;GO ROUND
	RET

;*********************************************************
;
;       $FADDS  FLOATING POINT ADDITION FOR SINGLE PRECISION
;               $FADDS FORMS THE SUM OF (BXDX) AND ($FAC) AND
;               LEAVES THE RESULT IN THE ($FAC).
;               
;       CALLING SEQUENCE:       CALL    $FADDS 
;       $FSUBS  FLOATING POINT SUBTRACTION FOR SINGLE PRECISION
;               $FSUBS FORMS THE DIFFERENCE (BXDX)-(FAC) AND
;               LEAVES THE RESULT IN THE (FAC).
;       CALLING SEQUENCE:       CALL    $FSUBS
;
;**********************************************************
FEXIT1: MOV     WORD PTR [FAC-1],BX      ;MOV (BXDX) TO $FAC
        MOV     WORD PTR [FACLO],DX
EXIT2:  RET
$FSUBS: MOV     AX,WORD PTR [FAC-1]      ;FETCH FAC
        OR      AH,AH           ;IF ZF=1 (BXDX) IS ANSWER
        JZ      FEXIT1          ;(BXDX) IS THE ANSWER
        XOR     BYTE PTR [FAC-1],0x80 ;FLIP SIGN
$FADDS:                 ;($FAC)=(BXDX)+($FAC)
        OR      BH,BH           ;WILL FIRST CHECK EXPONENT OF (BXDX)
        JZ      EXIT2           ;ANS ALREADY IN $FAC
        MOV     AX,WORD PTR [FAC-1]      ;WILL NOW CHECK $FAC AND IF ZERO
        OR      AH,AH           ;ANSWER IN (BXDX) AND MUST MOVE
        JZ      FEXIT1          ;MOVE (BXDX) TO FAC
                                ;****************************************************
                                ;KNOW AT THIS POINT THAT NEITHER (BXDX) NOR THE
                                ;$FAC ARE ZERO. THE SUM WILL BE PERFORMED BY EXAMINATION
                                ;OF THE EXPONENTS, PLACING THE NUMBER WITH THE LARGER
                                ;EXPONENT IN THE $FAC,AND SHIFTING THE SMALLER NUMBER RIGHT
                                ;UNTIL BINARY POINTS ALIGN, THEN ADDING THE MANTISSAS
                                ;IF THE SIGNS ARE THE SAME OR SUBTRACTING THE MANTISSAS
                                ;IF THE SIGNS ARE DIFFERENT. THE EXPONENT OF THE ANSWER
                                ;IS THE EXPONENT OF THE LARGER NUMBER. THE FORMAT OF
                                ;FLOATING POINT NUMBERS IS AS FOLLOWS:
                                ;
                                ;BIT    33222222 22221111 11111100 00000000
                                ;       10987654 32109876 54321098 76543210
                                ;       AAAAAAAA BCCCCCCC CCCCCCCC CCCCCCCC
                                ;BYTE   [ $FAC ] [$FAC-1] [$FAC-2] [$FAC-3]
                                ;                                  [$FACLO]
                                ;
                                ;WHERE  A=BITS OF EXPONENT BIASED BY 128
                                ;       B=0 IF NUMBER IS POSITIVE,1 IF NEGATIVE
                                ;       C=BITS 2-24 OF MANTISSA(BIT 1 IS UNDERSTOOD 1)
                                ;NOTE:THE BINARY POINT IS TO THE LEFT OF THE UNDERSTOOD 1
                                ;
                                ;******************************************************

        XOR     CX,CX           ;(CX)=0
        MOV     SI,WORD PTR [FACLO]      ;(SI)=($FAC-2,$FACLO)
        MOV     BYTE PTR [FAC+1],AL      ;ASSUME SIGN OF $FAC
        MOV     CL,AH           ;SINCE ASSUME $FAC LARGER
        SUB     CL,BH           ;CL WILL HOLD SHIFT COUNT
        JNB     FA20            ;JUMP IF $FAC EXP EQUAL OR LARGER
        NEG     CL              ;NEED POS. SHIFT COUNT
        XCHG    BL,BH
        MOV     WORD PTR [FAC],BX        ;SINCE (BXDX) LARGER MAGNITUDE
        XCHG    BL,BH           ;GET EXP/SGN CORRECT AGAIN
        XCHG    BX,AX           ;WILL EXCHANGE (BXDX) AND (AXSI)
        XCHG    DX,SI           ;
FA20:                           ;********************************************************
                                ;AT THIS POINT SUSPECTED LARGER NUMBER IS IN (AXSI) WITH
                                ;SMALLER IN (BXDX). THIS WILL BE THE CASE UNLESS THE EXPONENTS
                                ;WERE EQUAL. IF THE EXPONENTS WERE EQUAL AND THIS IS
                                ;TO BE A SUBTRACTION A NEGATIVE MANTISSA COULD RESULT. IF THIS
                                ;HAPPENS, WE MUST COMPLEMENT THE MANTISSA AND THE SIGN OF THE
                                ;RESULT.
                                ;********************************************************
        MOV     AH,AL           ;WILL NOW DETERMINE IF ADD OR
        XOR     AH,BL           ;SUBTRACT
        PUSHF                   ;SF=1 IF SUBTRACT
        MOV     AH,0x80      ;WILL REPLACE UNDERSTOOD 1
        OR      AL,AH
        OR      BL,AH
        XOR     AH,AH           ;(AH) WILL BE OVERFLOW BYTE
        MOV     BH,AH           ;(AH)=(BH)=0
FA22:   OR      CX,CX           ;ZF=1 IF EXPONENTS THE SAME
        JZ      FA40            ;IF EXPONENTS SAME JUMP
        CMP     CX,31           ;MUST SEE IF WITHIN 24 BITS
        JB      FA23            ;IF SO PROCEED
;*************************************************************
;THE NUMBERS WE ARE TRYING TO ADD/SUBTRACT ARE OF SUCH DIFFERENCE
;IN MAGNITUDE THAT THE SMALLER IS NEGLIGIBLE WITH RESPECT TO THE
;LARGER. OUR ANSWER THEREFORE IS THE NUMBER WITH THE ABSOLUTE
;LARGER MAGNITUDE. THE MANTISSA OF THIS NO. IS IN (AL:SI)
;**************************************************************
        POPF                    ;CLEAR SUBTRACT/ADD FLAG
        MOV     WORD PTR [FACLO],SI      ;RESTORE LOWER MANTISSA BITS
        MOV     AH,BYTE PTR [FAC+1]      ;FETCH SIGN
        AND     AX,0x807f       ;CLEAR SIGN IN AH, ALL BUT SIGN IN AL
        OR      AL,AH           ;RESTORE SIGN
        MOV     BYTE PTR [FAC-1],AL      ;$FAC NOW CORRECTLY BUILT
        RET
FA23:
                                ;WILL TRY FOR BYTE MOVES
        CMP     CL,0x08         ;NEED AT LEAST 8 BITS
        JB      FA27            ;IF NOT PROCEED AS NORMAL
        MOV     DI,AX           ;WILL WANT TO CHECK THIS FOR ST
        MOV     AH,DL           ;SHIFT OVERFLOW BITS
        TEST    DI,0xff00       ;DID WE SHIFT THROUGH ST?
        JZ      FA24
        OR      AH,0x20         ;PUT ST BACK IN
FA24:
        MOV     DL,DH
        MOV     DH,BL
        XOR     BL,BL           ;CLEAR UPPER BITS
        SUB     CL,0x08
        TEST    AH,0x1f         ;SHIFT THRU ST
        JZ      FA22            ;IF NOT TRY AGAIN
        OR      AH,0x20
        JMP     FA22
FA25:   OR      AH,0x20         ;"OR" IN ST BIT
        LOOP    FA30            ;CONTINUE LOOP
        JMP     FA40            ;IF FINISHED JUMP
FA27:   CLC                     ;MAKE SURE CARRY CLEAR BEFORE SHIFT
FA30:   RCR     BL,1
        RCR     DX,1
        RCR     AH,1            ;SHIFT (BLDXAH)RIGHT ONE BIT
        TEST    AH,0x10         ;SEE IF ST SET
        JNZ     FA25
                                ;CARRY INTO HIGH BIT
        LOOP    FA30            ;LOOP UNTIL (CX)=0
FA40:   POPF                    ;IF SF=1 WE MUST SUBTRACT MANTISSAS
        JNS     FA50            ;IF SF=0 GO ADD MANTISSAS
        SUB     CL,AH           ;SUBTRACT UNDERFLOW BYTE
        MOV     AH,CL           ;MUST GO TO NORMS WITH MANT. IN (BLDXCL)
        SBB     SI,DX
        MOV     DX,SI
        SBB     AL,BL           ;IF CARRY (CF) NOT SET THEN
        MOV     BL,AL
        JNB     FA90            ;ASSUMPTION OF $FAC LARGER VALID
        NOT     BYTE PTR [FAC+1] ;MUST USE OTHER SIGN $FAC WASN'T
        NOT     AH              ;LARGER
        NOT     DX
        NOT     BL
        INC     AH              ;INCREMENT BY ONE AND SET CARRY
        JNZ     FA90            ;IF ZF=0 GO NORMALIZE
        INC     DX              ;INCREMENT BY ONE
        JNZ     FA90            ;IF ZF=0 GO NORMALIZE
        INC     BL              ;INCREMENT BY ONE
        JNZ     FA90            ;IF ZF=0 GO NORMALIZE
        JMP     FA60
FA50:
;************************************************************
;SIGNS OF THE NUMBERS WERE THE SAME SO WE ADD MANTISSAS HERE
;*************************************************************
        ADD     DX,SI           ;ADDITION OF LOW BITS
        ADC     BL,AL           ;ADDITION OF HIGH BITS
        JNB     FA70
FA60:                           ;HERE WHEN WE HAVE OVERFLOWED THE HIGH MANTISSA BYTE
                                ;AND MUST INCREMENT THE EXPONENT
        INC     BYTE PTR [FAC]   ;INCREMENT THE EXPONENT
        JZ      FA80            ;OVERFLOW!
        RCR     BL,1            ;MUST SHIFT RIGHT ONE BIT
        RCR     DX,1
        RCR     AH,1
FA70:   JMP     $ROUNS
FA80:   JMP     $OVFLS          ;DO OVERFLOW CODE
FA90:   JMP     $NORMS          ;GO NORMALIZE

;************************************************************
;
;       $NORMS  SINGLE PRECISION NORMALIZATION ROUTINE
;               $NORMS SHIFTS (BLDXAH) LEFT UNTIL THE SIGN
;               BIT OF (BL)IS 1. FOR EACH LEFT SHIFT
;               $NORMS WILL DECREMENT THE FAC
;               ONCE THIS PROCESS IS COMPLETE, $NORMS WILL
;               JUMP TO $ROUNS TO ROUND THE NUMBER AND
;               PACK IT INTO THE FAC BYTES.
;
;*************************************************************

$NORMS:
        MOV     BH,BYTE PTR [FAC]        ;EXPONENT TO BH
        MOV     CX,4
NOR10:  OR      BL,BL           ;SEE IF SIGN BIT SET
        JS      NOR20           ;IF SO NORMALIZATION COMPLETE
        JNZ     NOR15           ;UPPER BYTE NON-ZERO
        SUB     BH,0x08         ;CAN WE SUBTRACT 8 W/O UNDERFLOW?
        JBE     NOR17
        MOV     BL,DH
        MOV     DH,DL
        MOV     DL,AH
        XOR     AH,AH           ;CLEAR OVERFLOW BYTE
        LOOP    NOR10
        JZ      NOR17           ;UNDERFLOW!
NOR15:
        CLC                     ;CLEAR CARRY FLAG [CF]
        RCL     AH,1            ;SHIFT OVERFLOW BYTE LEFT.
        RCL     DX,1            ;SHIFT LOWER MANTISSA WORD LEFT
        RCL     BL,1            ;SHIFT HIGH MANTISSA BYTE LEFT
NOR16:  DEC     BH              ;DECREMENT EXPONENT
        JNZ     NOR10           ;CONTINUE UNLESS UNDERFLOW
NOR17:  JMP     $ZERO           ;ZERO THE FAC AND RETURN
NOR20:  MOV     BYTE PTR [FAC],BH        ;UPDATE EXPONENT
        JMP     $ROUNS

;****************************************************************
;       $FLT    CONVERTS THE SIGNED INTEGER IN (DX) TO A REAL
;               (FLOATING POINT ) NUMBER AND STORES IT IN THE FAC
;               AND SETS $VALTP=4
;*****************************************************************
$FLT:   XOR     BX,BX           ;CLEAR HIGH MANTISSA BYTE (BL)
        XOR     AH,AH           ;CLEAR OVERFLOW BYTE
        MOV     SI,FAC+1        ;FETCH $FAC ADDRESS TO (SI)
        MOV     BYTE PTR [SI-1],0x90 ;SET EXPONENT TO 16
        MOV     BYTE PTR [SI],0    ;SET SIGN POSITIVE
        OR      DX,DX           ;SETS SF=1 IF NEGATIVE NO.
        JNS     FLT10           ;IF POSITIVE PROCEED
        NEG     DX              ;NEED POSTIVE MAGNITUDE
        MOV     BYTE PTR 0[SI],0x80  ;SET SIGN TO NEGATIVE
FLT10:  MOV     BL,DH           ;WILL MOVE (DX) TO (BLDH)
        MOV     DH,DL           ;
        MOV     DL,BH           ;SET (DL)=0
        MOV     BYTE PTR [VALTP],4   ;SET TYPE TO S.P.
        JMP     $NORMS          ;GO NORMALIZE



DOIT:
	CALL $FLT
	HLT
