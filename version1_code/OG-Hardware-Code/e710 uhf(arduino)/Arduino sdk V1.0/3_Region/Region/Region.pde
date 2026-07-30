/*
  UHF RFID Set/Get RFID Tx Power
 
 This example works only on the Arduino Mega 2560
 
 Serial port 1, connect to RFID module, baudrate = 115200
 Main Serial port, print Version msg, baudrate = 115200
 
 */
#define rfidSerial              Serial1

#define	RFID_FRAME_SOF1         0xA5
#define	RFID_FRAME_SOF2		0x5A
#define RFID_FRAME_EOF1		0x0D
#define RFID_FRAME_EOF2		0x0A

#define	RFID_FRAME_SOF_LEN	2
#define	RFID_FRAME_EOF_LEN	2
#define RFID_FRAME_LEN_LEN	2
#define	RFID_FRAME_CMD_LEN	1
#define	RFID_FRAME_CHK_LEN	1

#define RFID_FRAME_FIXED_LEN	(RFID_FRAME_SOF_LEN + RFID_FRAME_EOF_LEN + RFID_FRAME_LEN_LEN + RFID_FRAME_CMD_LEN + RFID_FRAME_CHK_LEN)

typedef enum
{
  RT_FALSE			 	 = 0,
  RT_TRUE			   	    ,
}
emReturnStateDef;

typedef struct
{
  byte			u8Sof1;			// header1
  byte			u8Sof2;			// header2
  byte			u8Len1;			// length
  byte			u8Len2;			// length
  byte 		        u8Cmd;			// cmd
  byte    		pData[250];
  byte                  u8Chk;			// CRC
  byte  		u8Eof1;			// end1
  byte			u8Eof2;			// end2
  byte			bCheckRet;
  byte       		bProcessing;
  byte       		bGetDataComplete;
}
stUartRecvFrameDef;

stUartRecvFrameDef stHostifRecvFrame;
byte u8HeadCnt = 0;	  // 帧头字节数
byte u8DataIdx = 0;	  // 接收帧数据索引
byte u8CalChk = 0;        // 计算校验值


// Calculate Frame check
byte Cal_Xor(byte *pBuf, int u16Len)
{
  byte	crc = 0;
  int	i;

  for (i=0; i<u16Len; i++)
  {
    crc ^= pBuf[i];
  }

  return crc;
}

// build rfid module communicate frame
int Build_RFID_Frame(byte u8Cmd, byte *pInData, int u16InLen, byte *pOutData, int *u16OutLen)
{
  int	cur = 0, i;

  /* frame header */
  pOutData[cur++] = RFID_FRAME_SOF1;
  pOutData[cur++] = RFID_FRAME_SOF2;
  /* length */
  pOutData[cur++] = ((u16InLen + RFID_FRAME_FIXED_LEN) >> 8) & 0xFF;
  pOutData[cur++] = (u16InLen + RFID_FRAME_FIXED_LEN) & 0xFF;
  /* cmd */
  pOutData[cur++] = u8Cmd;
  /* data */
  for (i=0; i<u16InLen; i++)
  {
    pOutData[cur++] = pInData[i];
  }
  /* frame check */
  pOutData[cur++] = Cal_Xor(&pOutData[2], (u16InLen+3));
  /* frame end */
  pOutData[cur++] = RFID_FRAME_EOF1;
  pOutData[cur++] = RFID_FRAME_EOF2;

  *u16OutLen = cur;

  return 0;
}

// serial send one frame data to rfid
void serialSendFrameToRFID(byte *sbuf, int len)
{
  rfidSerial.write(sbuf, len);
}

// Clear rfid serial buffer
void ClearrfidSerialReceiveBuffer(void)
{
  while(rfidSerial.read() >= 0) {
  }
}

// parse rfid frame
void Hostif_Parse_Frame(void)
{
  byte u8Data;

  if (rfidSerial.available() > 0)      // is receive data
  {	
    if (stHostifRecvFrame.bProcessing)
    {
      return;
    }

    u8Data = rfidSerial.read();

    if ( u8HeadCnt < 5 )				
    {
      switch (u8HeadCnt)	// get header data
      {
      case 0:																		// 帧头，高字节
        {
          if ( u8Data == RFID_FRAME_SOF1 )
          {
            u8HeadCnt++;
            stHostifRecvFrame.u8Sof1 	= u8Data;
          }
          break;		
        }
      case 1:																		// 帧头，低字节
        {
          if ( u8Data == RFID_FRAME_SOF2 )
          {
            u8HeadCnt++;
            stHostifRecvFrame.u8Sof2 = u8Data;
            u8CalChk = 0;
          }
          else
          {
            u8HeadCnt = 0;
          }
          break;		
        }

      case 2:																		// 帧长度，高字节
        {
          stHostifRecvFrame.u8Len1 = u8Data;
          u8HeadCnt++;
          u8CalChk 	^= u8Data;

          break;
        }

      case 3:																		// 帧长度，低字节
        {
          stHostifRecvFrame.u8Len2 = u8Data;
          u8HeadCnt++;
          u8CalChk ^= u8Data;	
          break;
        }

      case 4:																		// 帧类型
        {
          u8HeadCnt++;
          stHostifRecvFrame.u8Cmd = u8Data;
          u8CalChk ^= u8Data;

          u8DataIdx = 0;
          break;
        }
      }
    }
    else if (u8DataIdx < (stHostifRecvFrame.u8Len2 - RFID_FRAME_FIXED_LEN))			// 帧数据
    {
      stHostifRecvFrame.pData[u8DataIdx++] = u8Data;
      u8CalChk ^= u8Data;
    }
    else if (u8DataIdx == (stHostifRecvFrame.u8Len2 - RFID_FRAME_FIXED_LEN))			// CRC
    {
      if (u8CalChk != u8Data)									// check u8Data
      {
        u8HeadCnt = 0;
        u8CalChk = 0;
      }
      stHostifRecvFrame.u8Chk = u8Data;
      u8DataIdx++;
    }
    else if (u8DataIdx == (stHostifRecvFrame.u8Len2 - RFID_FRAME_FIXED_LEN + 1))
    {
      if (u8Data == RFID_FRAME_EOF1)												// 帧尾，高字节
      {
        stHostifRecvFrame.u8Eof1 = u8Data;
        u8DataIdx++;
      }
      else
      {
        u8HeadCnt = 0;
        u8CalChk = 0;
      }
    }
    else if (u8DataIdx == (stHostifRecvFrame.u8Len2 - RFID_FRAME_FIXED_LEN + 2))
    {
      if (u8Data == RFID_FRAME_EOF2)												// 帧尾，低字节
      {
        stHostifRecvFrame.u8Eof2 = u8Data;
        stHostifRecvFrame.bCheckRet = RT_TRUE;
        stHostifRecvFrame.bGetDataComplete = RT_TRUE; 		           
        stHostifRecvFrame.bProcessing = RT_TRUE;
      }
      else
      {
        stHostifRecvFrame.bCheckRet = RT_FALSE;
      }

      u8HeadCnt = 0;
      u8CalChk = 0;
      u8DataIdx	= 0;
    }
    else
    {
      u8HeadCnt = 0;
      u8CalChk = 0;
      u8DataIdx	= 0;
    }
  }
}

// handle
byte Rfid_Handle_Command(void)
{
  byte	ret = RT_FALSE;

  if((stHostifRecvFrame.bGetDataComplete == RT_TRUE) && (stHostifRecvFrame.bCheckRet == RT_TRUE))
  {
    switch (stHostifRecvFrame.u8Cmd)
    {
    case 0x01:		// Get Hardware Version response
      {
        break;
      }

    default:	//其它命令直接透传
      break;
    }

    ret = RT_TRUE;

    stHostifRecvFrame.bProcessing = RT_FALSE;
    stHostifRecvFrame.bGetDataComplete = RT_FALSE;
  }

  return ret;
}

// get hardware version
byte GetHardwareVersion(byte *ver)
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE;
  int sendlen = 0;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  Build_RFID_Frame(0x00, tmp, 0, sendbuf, &sendlen);      // cmd = 0x00
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == 0x01)
      {
        memcpy(ver, stHostifRecvFrame.pData, 3);
        ret = RT_TRUE;
        break;
      }
    }
  }

  return ret;
}

// get firmware version
byte GetFirmwareVersion(byte *ver)            
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE;
  int sendlen = 0;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  Build_RFID_Frame(0x02, tmp, 0, sendbuf, &sendlen);        // cmd = 0x02
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == 0x03)
      {
        memcpy(ver, stHostifRecvFrame.pData, 3);
        ret = RT_TRUE;
        break;
      }
    }
  }

  return ret;
}

// set tx power
// antid: if antid = 0, The setting is valid for all antennas 
// rPow:  inventory power value
// wPow:  write, lock, kill operation power value
// saveflag: = 1, Save after power off, = 0, not save after power off
byte SetRFIDTxPower(byte antid, float rPow, float wPow, byte saveflag)            
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE;
  int sendlen = 0, cur = 0;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  tmp[cur++]  = (saveflag<<1);
  tmp[cur++]  = antid;
  tmp[cur++]  = (byte)((int)(rPow*100.0) >> 8);
  tmp[cur++]  = (byte)((int)(rPow*100.0) & 0xFF);
  tmp[cur++]  = (byte)((int)(wPow*100.0) >> 8);
  tmp[cur++]  = (byte)((int)(wPow*100.0) & 0xFF);
  Build_RFID_Frame(0x10, tmp, cur, sendbuf, &sendlen);        // cmd = 0x10 
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == 0x11)
      {
        if (stHostifRecvFrame.pData[0] == 0x01)             // set ok
            ret = RT_TRUE;
        
        break;
      }
    }
  }

  return ret;
}

// get tx power
byte GetRFIDTxPower(byte *NumOfPort, float *rPow, float *wPow)            
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE;
  int sendlen = 0, cur = 0, i;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  Build_RFID_Frame(0x12, tmp, cur, sendbuf, &sendlen);        // cmd = 0x12 
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == 0x13)
      {
        *NumOfPort = (stHostifRecvFrame.u8Len2 - 9) / 5;
        for (i=0; i<*NumOfPort; i++)
        {
            rPow[i] = (float)((stHostifRecvFrame.pData[(5*i) + 2] * 256) + stHostifRecvFrame.pData[(5*i) + 3])*0.01;
            wPow[i] = (float)((stHostifRecvFrame.pData[(5*i) + 4] * 256) + stHostifRecvFrame.pData[(5*i) + 5])*0.01;
        }
        
        ret = RT_TRUE;        
        break;
      }
    }
  }

  return ret;
}
//get region
//China1 0x01 
//China2 0x02 
//Europe 0x04
//USA 0x08 
//Korea 0x16
//Japan 0x32 
//Brazil 0x33
//WR1 0x34 
//South Africa 0x35
//Vietnam 0x36 
//INDIA 0x37
//TAIWAN 0x38 
//CHILE 0x39
//Uruguay 0x3A 
//Australia 0x3B
//New Zealand 0x3C 
//Europe 2 0x3D
byte SetRFIDRegion(byte region, byte saveflag) 
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0, i;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  cmd = 0x2C;
  tmp[cur++]  = saveflag;
  tmp[cur++]  = region;
  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0x2C 
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == cmd+1)
      {
        if (stHostifRecvFrame.pData[0] == 0x01)
        {
            ret = RT_TRUE;     
        }           
        break;
      }
    }
  }

  return ret;
}
//get region
//China1 0x01 
//China2 0x02 
//Europe 0x04
//USA 0x08 
//Korea 0x16
//Japan 0x32 
//Brazil 0x33
//WR1 0x34 
//South Africa 0x35
//Vietnam 0x36 
//INDIA 0x37
//TAIWAN 0x38 
//CHILE 0x39
//Uruguay 0x3A 
//Australia 0x3B
//New Zealand 0x3C 
//Europe 2 0x3D
byte GetRFIDRegion(byte *region)            
{
  byte tmp[100], sendbuf[100], ret = RT_FALSE, cmd;
  int sendlen = 0, cur = 0, i;
  long timeout = 0x80000;      // time out (2300ms for Mega 2560)

  cmd = 0x2E;
  Build_RFID_Frame(cmd, tmp, cur, sendbuf, &sendlen);        // cmd = 0x2E 
  serialSendFrameToRFID(sendbuf, sendlen);

  while(timeout--)
  {
    Hostif_Parse_Frame();
    if (RT_TRUE == Rfid_Handle_Command())
    {
      if (stHostifRecvFrame.u8Cmd == cmd+1)
      {
        if (stHostifRecvFrame.pData[0] == 0x01)
        {
            *region = stHostifRecvFrame.pData[1];
            ret = RT_TRUE;     
        }           
        break;
      }
    }
  }

  return ret;
}

void setup() {

  Serial.begin(115200);
  rfidSerial.begin(115200);
  
  byte region, result;
  
  // test Set region
  region = 0x04;              // 0x04 = Europe(865.7 866.3 866.9 867.5)
  Serial.println("SetRFIDRegion!");
  result = SetRFIDRegion(region, 1);                // saveflag = 1
  if (result == RT_TRUE)
  {
    Serial.println("Set OK!");
  }
  else
  {
    Serial.println("Set failed!");
  }  
  
  
  // test Get region
  Serial.println("GetRFIDRegion!");
  result = GetRFIDRegion(&region);
  if (result == RT_TRUE)
  {
    Serial.println("Get OK!");
    
    switch(region)
    {
        case 0x01:
            Serial.println("Region = China1");
            break;
        case 0x02:
            Serial.println("Region = China2");
            break;
        case 0x04:
            Serial.println("Region = Europe(865.7 866.3 866.9 867.5)");
            break;
        case 0x08:
            Serial.println("Region = USA");
            break;
        case 0x016:
            Serial.println("Region = Korea");
            break;
        case 0x32:
            Serial.println("Region = Japan");
            break;
        case 0x33:
            Serial.println("Region = Brazil");
            break;
        case 0x34:
            Serial.println("Region = WR1");
            break;              
        case 0x35:
            Serial.println("Region = South Africa");
            break;
        case 0x36:
            Serial.println("Region = Vietnam");
            break;
        case 0x37:
            Serial.println("Region = INDIA");
            break;
        case 0x38:
            Serial.println("Region = TAIWAN");
            break;
        case 0x39:
            Serial.println("Region = CHILE");
            break;
        case 0x3A:
            Serial.println("Region = Uruguay");
            break;
        case 0x3B:
            Serial.println("Region = Australia");
            break;
        case 0x3C:
            Serial.println("Region = New Zealand");
            break;
        case 0x3D:
            Serial.println("Region = Europe 2(916.3 917.5 918.7 919.9)");
            break;  
        default:
            Serial.println("Region = NONE");
            break;  
    }
  }
  else
  {
    Serial.println("Get failed!");
  }
}

void loop() {

  Serial.println("Region Set and Get test!");
  delay(1000);
}
